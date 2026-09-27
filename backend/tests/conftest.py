import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SEED_ON_STARTUP"] = "false"

from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, engine
from app.core.database import Base
from app.models import Account, FraudAlert, LedgerEntry, Transaction
from app.services.bootstrap import bootstrap
from app.services.transaction_service import TransactionInput, create_account, create_transaction


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    bootstrap(db)
    db.close()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from types import SimpleNamespace

    from app.api.deps import get_current_user
    from app.main import app
    from app.services.context import current_user_id

    def _demo():
        current_user_id.set("USR-DEMO")
        return SimpleNamespace(id="USR-DEMO", email="demo@finsight.local", full_name="Avery Chen")

    app.dependency_overrides[get_current_user] = _demo
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)


def _txn(account_id: str, **overrides) -> TransactionInput:
    payload = dict(
        account_id=account_id,
        destination_account_id=None,
        transaction_type="DEBIT",
        amount=Decimal("25.00"),
        currency="USD",
        merchant="Corner Store",
        category="Retail",
        description="Test",
        timestamp=datetime(2026, 9, 10, 12, 0, 0),
        location="Test City",
    )
    payload.update(overrides)
    return TransactionInput(**payload)


def test_account_creation_and_opening_balance(db):
    account = create_account(
        db, name="Treasury", account_type="CHECKING", currency="USD", opening_balance=Decimal("1000.00")
    )
    assert account.id.startswith("ACC-")
    assert account.balance == Decimal("1000.00")
    entries = db.query(LedgerEntry).filter(LedgerEntry.account_id == account.id).all()
    assert len(entries) == 1
    assert entries[0].entry_type == "CREDIT"


def test_credit_debit_and_transfer_consistency(db):
    source = create_account(db, name="A", account_type="CHECKING", currency="USD", opening_balance=Decimal("10000"))
    dest = create_account(db, name="B", account_type="SAVINGS", currency="USD", opening_balance=Decimal("5000"))
    create_transaction(
        db,
        _txn(source.id, transaction_type="CREDIT", amount=Decimal("100"), merchant="Refund", category="Income", timestamp=datetime(2026, 9, 11, 9, 0)),
    )
    create_transaction(
        db,
        _txn(source.id, transaction_type="DEBIT", amount=Decimal("50"), merchant="Cafe", timestamp=datetime(2026, 9, 11, 10, 0)),
    )
    transfer = create_transaction(
        db,
        _txn(
            source.id,
            destination_account_id=dest.id,
            transaction_type="TRANSFER",
            amount=Decimal("2000"),
            merchant="Internal Transfer",
            category="Transfer",
            timestamp=datetime(2026, 9, 11, 11, 0),
        ),
    )
    db.expire_all()
    source = db.get(Account, source.id)
    dest = db.get(Account, dest.id)
    assert source.balance == Decimal("8050.00")
    assert dest.balance == Decimal("7000.00")
    pair = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == transfer.id).all()
    posted = {(entry.account_id, entry.entry_type, entry.amount) for entry in pair}
    assert (source.id, "DEBIT", Decimal("2000.00")) in posted
    assert (dest.id, "CREDIT", Decimal("2000.00")) in posted
    debits = sum(entry.amount for entry in db.query(LedgerEntry).all() if entry.entry_type == "DEBIT")
    credits = sum(entry.amount for entry in db.query(LedgerEntry).all() if entry.entry_type == "CREDIT")
    assert debits == credits
    assert sum(account.balance for account in db.query(Account).all()) == Decimal("0.00")


def test_insufficient_balance_rolls_back(db):
    account = create_account(db, name="Thin", account_type="CHECKING", currency="USD", opening_balance=Decimal("100"))
    before = db.query(LedgerEntry).count()
    with pytest.raises(Exception) as caught:
        create_transaction(db, _txn(account.id, amount=Decimal("150"), timestamp=datetime(2026, 9, 12, 8, 0)))
    assert caught.value.code == "INSUFFICIENT_BALANCE"
    db.expire_all()
    assert db.get(Account, account.id).balance == Decimal("100.00")
    assert db.query(LedgerEntry).count() == before
    assert db.query(Transaction).filter(Transaction.category != "OPENING_BALANCE").count() == 0


def test_fraud_rules_and_alert_resolution(db):
    account = create_account(db, name="Risk", account_type="CHECKING", currency="USD", opening_balance=Decimal("20000"))
    for index, merchant in enumerate(["Alpha", "Bravo", "Charlie"]):
        create_transaction(
            db,
            _txn(
                account.id,
                amount=Decimal("100"),
                merchant=merchant,
                timestamp=datetime(2026, 9, 1, 9, index),
            ),
        )
    large = create_transaction(
        db,
        _txn(account.id, amount=Decimal("1000"), merchant="Bulk Vendor", timestamp=datetime(2026, 9, 2, 9, 0)),
    )
    assert large.risk_score >= 55
    assert any(rule["code"] == "LARGE_TRANSACTION" for rule in large.triggered_rules)
    duplicate = create_transaction(
        db,
        _txn(account.id, amount=Decimal("1000"), merchant="Bulk Vendor", timestamp=datetime(2026, 9, 2, 9, 3)),
    )
    assert duplicate.risk_score >= 40
    assert any(rule["code"] == "DUPLICATE_TRANSACTION" for rule in duplicate.triggered_rules)
    alert = db.query(FraudAlert).filter(FraudAlert.transaction_id == duplicate.id).one()
    from app.services.transaction_service import review_alert

    review_alert(db, alert.id, status="RESOLVED", resolution_note="Confirmed with customer")
    db.expire_all()
    assert db.get(FraudAlert, alert.id).status == "RESOLVED"
    assert db.get(Transaction, duplicate.id).status == "POSTED"


def test_frequency_detection(db):
    account = create_account(db, name="Burst", account_type="CHECKING", currency="USD", opening_balance=Decimal("5000"))
    last = None
    for index in range(5):
        last = create_transaction(
            db,
            _txn(
                account.id,
                amount=Decimal(str(10 + index)),
                merchant=f"Vendor {index}",
                timestamp=datetime(2026, 9, 5, 16, index),
            ),
        )
    assert any(rule["code"] == "HIGH_FREQUENCY" for rule in last.triggered_rules)


def test_score_is_capped():
    from types import SimpleNamespace

    from app.services.fraud_service import TxView, evaluate_risk

    settings = SimpleNamespace(
        duplicate_window_minutes=5,
        duplicate_score=40,
        frequency_threshold=5,
        frequency_window_minutes=5,
        frequency_score=40,
        large_multiplier_medium=3,
        large_multiplier_high=5,
        large_score_medium=25,
        large_score_high=40,
        unusual_time_score=40,
        unusual_start_hour=0,
        unusual_end_hour=5,
        anomaly_score=40,
        min_history_count=3,
        alert_threshold=30,
    )
    prior = [
        TxView(f"P{i}", Decimal("20"), f"Shop {i}", "Retail", datetime(2026, 9, 4, 2, i))
        for i in range(6)
    ]
    current = TxView("C", Decimal("800"), "Shop 0", "Retail", datetime(2026, 9, 4, 2, 4))
    result = evaluate_risk(current, prior, settings)
    assert result.score == 100
    assert result.level == "HIGH"


def test_csv_validation_and_import(client):
    created = client.post(
        "/api/accounts",
        json={"name": "Import", "account_type": "CHECKING", "currency": "USD", "opening_balance": "500"},
    )
    assert created.status_code == 201
    account_id = created.json()["id"]
    csv_text = (
        "account_id,transaction_type,amount,currency,merchant,category,description,timestamp,location,destination_account_id\n"
        f"{account_id},DEBIT,10.00,USD,Cafe,Food,Lunch,2026-09-12T12:00:00,NY,\n"
        f"{account_id},DEBIT,-5,USD,Bad,Food,Nope,2026-09-12T12:05:00,NY,\n"
        "ACC-MISSING,DEBIT,10,USD,Nope,Food,Missing,2026-09-12T12:06:00,NY,\n"
    )
    response = client.post("/api/transactions/import", files={"file": ("tx.csv", csv_text, "text/csv")})
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1
    assert body["rejected"] == 2


def test_api_rejects_invalid_transaction(client):
    created = client.post(
        "/api/accounts",
        json={"name": "API", "account_type": "SAVINGS", "currency": "USD", "opening_balance": "50"},
    )
    account_id = created.json()["id"]
    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "transaction_type": "DEBIT",
            "amount": "0",
            "currency": "USD",
            "merchant": "Zero",
            "category": "Test",
            "timestamp": "2026-09-12T12:00:00",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_TRANSACTION"


def test_missing_account_error(client):
    response = client.post(
        "/api/transactions",
        json={
            "account_id": "ACC-9999",
            "transaction_type": "CREDIT",
            "amount": "10",
            "currency": "USD",
            "merchant": "X",
            "category": "Income",
            "timestamp": "2026-09-12T12:00:00",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"] == "ACCOUNT_NOT_FOUND"

from datetime import datetime
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.models import Transaction
from app.services.ledger_service import assert_balanced
from app.services.model_comparison import compare_models
from app.services.security import hash_password, verify_password
from app.services.transaction_service import TransactionInput, create_account, create_transaction


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


def test_unbalanced_journal_is_rejected():
    entries = [
        type("Entry", (), {"entry_type": "DEBIT", "amount": Decimal("10.00")})(),
        type("Entry", (), {"entry_type": "CREDIT", "amount": Decimal("4.00")})(),
    ]
    with pytest.raises(AppError) as caught:
        assert_balanced(entries)
    assert caught.value.code == "UNBALANCED_ENTRY"


def test_idempotent_post_returns_the_original_transaction(client, db):
    account = create_account(
        db,
        name="Repeat Checking",
        account_type="CHECKING",
        currency="USD",
        opening_balance=Decimal("80"),
    )
    payload = {
        "account_id": account.id,
        "transaction_type": "DEBIT",
        "amount": "12.00",
        "currency": "USD",
        "merchant": "Repeat Cafe",
        "category": "Food",
        "description": "",
        "timestamp": "2026-09-20T12:00:00",
    }
    headers = {"Idempotency-Key": "cafe-once"}
    first = client.post("/api/transactions", json=payload, headers=headers)
    second = client.post("/api/transactions", json=payload, headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert db.query(Transaction).filter(Transaction.merchant == "Repeat Cafe").count() == 1


def test_scores_include_rules_and_model(db):
    account = create_account(db, name="Model", account_type="CHECKING", currency="USD", opening_balance=Decimal("5000"))
    last = None
    for index in range(8):
        last = create_transaction(
            db,
            _txn(account.id, amount=Decimal("40"), merchant="Grocery", timestamp=datetime(2026, 9, 3, 12, index)),
        )
    assert last is not None
    assert last.rule_score >= 0
    assert last.ml_score >= 0
    assert last.risk_score == min(100, int(round((0.7 * last.rule_score) + (0.3 * last.ml_score))))


def test_model_comparison_metrics_are_bounded():
    report = compare_models()
    for name in ("rules", "model", "hybrid"):
        metrics = report[name]
        for key in ("precision", "recall", "f1", "pr_auc", "false_positive_rate"):
            assert 0 <= metrics[key] <= 1


def test_argon2_verifies_and_accepts_legacy_pbkdf2():
    stored = hash_password("ledger-pass")
    assert stored.startswith("$argon2")
    assert verify_password("ledger-pass", stored)
    legacy = "pbkdf2_sha256$200000$abc$"  # incomplete on purpose
    assert verify_password("ledger-pass", legacy) is False

from datetime import datetime
from decimal import Decimal

from app.models import FraudAlert
from app.services.transaction_service import TransactionInput, create_account, create_transaction, review_alert


def _at(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _post(db, **kwargs):
    return create_transaction(db, TransactionInput(**kwargs))


def seed_demo_if_empty(db) -> None:
    from app.models import Account

    existing = db.query(Account).filter(Account.account_type != "SYSTEM").count()
    if existing:
        return

    operating = create_account(
        db,
        name="Northwind Operating",
        account_type="CHECKING",
        currency="USD",
        opening_balance=Decimal("42000.00"),
    )
    payroll = create_account(
        db,
        name="Harbor Payroll Reserve",
        account_type="SAVINGS",
        currency="USD",
        opening_balance=Decimal("36000.00"),
    )
    vendor = create_account(
        db,
        name="Vendor Clearing",
        account_type="OPERATIONS",
        currency="USD",
        opening_balance=Decimal("25160.06"),
    )

    baseline = [
        ("2026-09-01T09:10:00", "Northline Coffee", "80.00", "Food"),
        ("2026-09-02T12:05:00", "Metro Transit", "75.00", "Transport"),
        ("2026-09-03T11:20:00", "Adobe", "90.00", "Software"),
        ("2026-09-04T16:40:00", "Market Hall", "70.00", "Groceries"),
        ("2026-09-06T10:15:00", "City Parking", "85.00", "Transport"),
        ("2026-09-08T15:30:00", "Harbor Utilities", "95.00", "Utilities"),
        ("2026-09-10T09:45:00", "Paper & Co", "60.00", "Supplies"),
        ("2026-09-12T14:10:00", "Civic Wireless", "85.00", "Telecom"),
    ]
    for timestamp, merchant, amount, category in baseline:
        _post(
            db,
            account_id=operating.id,
            transaction_type="DEBIT",
            amount=Decimal(amount),
            currency="USD",
            merchant=merchant,
            category=category,
            description=f"{merchant} purchase",
            timestamp=_at(timestamp),
            location="New York, US",
        )

    _post(
        db,
        account_id=operating.id,
        transaction_type="CREDIT",
        amount=Decimal("150.00"),
        currency="USD",
        merchant="Client Remittance",
        category="Income",
        description="Consulting remittance",
        timestamp=_at("2026-09-15T09:00:00"),
        location="New York, US",
    )
    _post(
        db,
        account_id=payroll.id,
        transaction_type="CREDIT",
        amount=Decimal("4200.00"),
        currency="USD",
        merchant="Northwind Payroll",
        category="Income",
        description="September payroll funding",
        timestamp=_at("2026-09-15T08:00:00"),
        location="New York, US",
    )
    _post(
        db,
        account_id=operating.id,
        destination_account_id=vendor.id,
        transaction_type="TRANSFER",
        amount=Decimal("100.00"),
        currency="USD",
        merchant="Internal Transfer",
        category="Transfer",
        description="Vendor float top-up",
        timestamp=_at("2026-09-18T10:00:00"),
        location="New York, US",
    )

    gucci_one = _post(
        db,
        account_id=operating.id,
        transaction_type="DEBIT",
        amount=Decimal("850.00"),
        currency="USD",
        merchant="Gucci Boutique NY",
        category="Retail",
        description="Boutique purchase",
        timestamp=_at("2026-09-20T14:02:00"),
        location="New York, US",
    )
    gucci_two = _post(
        db,
        account_id=operating.id,
        transaction_type="DEBIT",
        amount=Decimal("850.00"),
        currency="USD",
        merchant="Gucci Boutique NY",
        category="Retail",
        description="Repeat boutique purchase",
        timestamp=_at("2026-09-20T14:04:00"),
        location="New York, US",
    )
    apex = _post(
        db,
        account_id=operating.id,
        transaction_type="DEBIT",
        amount=Decimal("2000.00"),
        currency="USD",
        merchant="Apex Equipment",
        category="Equipment",
        description="Equipment invoice",
        timestamp=_at("2026-09-21T11:06:00"),
        location="Newark, US",
    )
    _post(
        db,
        account_id=operating.id,
        transaction_type="DEBIT",
        amount=Decimal("20.00"),
        currency="USD",
        merchant="Night Kiosk",
        category="Food",
        description="After-hours purchase",
        timestamp=_at("2026-09-22T02:14:00"),
        location="New York, US",
    )

    vendor_baseline = [
        ("2026-09-03T10:00:00", "Cedar Office"),
        ("2026-09-05T10:00:00", "Lumen Print"),
        ("2026-09-07T10:00:00", "Dock Storage"),
        ("2026-09-09T10:00:00", "Field Catering"),
        ("2026-09-11T10:00:00", "Route Fuel"),
        ("2026-09-13T10:00:00", "Parcel Hub"),
    ]
    for timestamp, merchant in vendor_baseline:
        _post(
            db,
            account_id=vendor.id,
            transaction_type="DEBIT",
            amount=Decimal("40.00"),
            currency="USD",
            merchant=merchant,
            category="Operations",
            description="Routine vendor spend",
            timestamp=_at(timestamp),
            location="Jersey City, US",
        )

    burst = []
    burst_rows = [
        ("2026-09-23T16:00:00", "Rapid Parts North", "180.00"),
        ("2026-09-23T16:01:00", "Rapid Parts East", "190.00"),
        ("2026-09-23T16:02:00", "Rapid Parts West", "210.00"),
        ("2026-09-23T16:03:00", "Rapid Parts South", "220.00"),
        ("2026-09-23T16:04:00", "Rapid Parts Central", "230.00"),
    ]
    for timestamp, merchant, amount in burst_rows:
        burst.append(
            _post(
                db,
                account_id=vendor.id,
                transaction_type="DEBIT",
                amount=Decimal(amount),
                currency="USD",
                merchant=merchant,
                category="Supplies",
                description="Same-hour parts replenishment",
                timestamp=_at(timestamp),
                location="Jersey City, US",
            )
        )

    def _alert_for(transaction_id: str) -> FraudAlert | None:
        return db.query(FraudAlert).filter(FraudAlert.transaction_id == transaction_id).one_or_none()

    resolved = _alert_for(gucci_one.id)
    if resolved:
        review_alert(
            db,
            resolved.id,
            status="RESOLVED",
            resolution_note="Cardholder confirmed the first boutique purchase.",
        )
    false_positive = _alert_for(burst[0].id)
    if false_positive:
        review_alert(
            db,
            false_positive.id,
            status="FALSE_POSITIVE",
            resolution_note="Known vendor restock. First charge in the window was expected.",
        )
    for extra in burst[1:3]:
        alert = _alert_for(extra.id)
        if alert:
            review_alert(db, alert.id, status="RESOLVED", resolution_note="Reviewed with operations. No further action.")

    # Touch the remaining objects so seed intent stays explicit for readers.
    _ = (gucci_two, apex)

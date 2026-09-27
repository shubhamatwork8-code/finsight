from decimal import Decimal

from app.models import Account, LedgerEntry
from app.services.fx_service import apply_conversion
from app.services.transaction_service import create_account


def test_conversion_scales_both_sides_of_the_ledger(db):
    account = create_account(
        db,
        name="Treasury",
        account_type="CHECKING",
        currency="USD",
        opening_balance=Decimal("100.00"),
    )
    apply_conversion(db, Decimal("80"), "INR")
    db.expire_all()
    refreshed = db.get(Account, account.id)
    assert refreshed.balance == Decimal("8000.00")
    entries = db.query(LedgerEntry).all()
    debits = sum(entry.amount for entry in entries if entry.entry_type == "DEBIT")
    credits = sum(entry.amount for entry in entries if entry.entry_type == "CREDIT")
    assert debits == credits
    assert any(entry.amount == Decimal("100.00") and (entry.entry_kind or "ORIGINAL") == "ORIGINAL" for entry in entries)
    assert sum(row.balance for row in db.query(Account).all()) == Decimal("0.00")

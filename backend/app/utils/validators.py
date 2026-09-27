from decimal import Decimal

from app.core.errors import AppError
from app.core.money import money


def require_positive_amount(amount: Decimal) -> Decimal:
    quantized = money(amount)
    if quantized <= 0:
        raise AppError("INVALID_TRANSACTION", "Amount must be positive")
    return quantized


LEDGER_CURRENCIES = ("USD", "EUR", "GBP", "INR", "AED", "SGD", "AUD", "CAD", "CHF", "JPY")


def require_currency(value: str) -> str:
    code = (value or "").strip().upper()
    if len(code) != 3 or not code.isalpha():
        raise AppError("INVALID_TRANSACTION", "Currency must be a 3-letter ISO code")
    return code

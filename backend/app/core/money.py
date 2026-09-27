from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator

TWOPLACES = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


class Money(TypeDecorator):
    impl = Numeric(14, 2)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return money(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return money(value)

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.money import Money
from app.core.timeutil import utcnow


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_ledger_amount_positive"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(10), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    generation: Mapped[int] = mapped_column(default=0)
    entry_kind: Mapped[str] = mapped_column(String(16), default="ORIGINAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    transaction = relationship("Transaction", back_populates="ledger_entries")
    account = relationship("Account", back_populates="ledger_entries")

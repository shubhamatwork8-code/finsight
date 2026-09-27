from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.money import Money
from app.core.timeutil import utcnow


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True)
    destination_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"), nullable=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    merchant: Mapped[str] = mapped_column(String(160), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="POSTED", index=True)
    risk_score: Mapped[int] = mapped_column(default=0)
    rule_score: Mapped[int] = mapped_column(default=0)
    ml_score: Mapped[int] = mapped_column(default=0)
    risk_level: Mapped[str] = mapped_column(String(10), default="LOW", index=True)
    risk_explanation: Mapped[str] = mapped_column(Text, default="")
    triggered_rules: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    account = relationship("Account", foreign_keys=[account_id])
    destination_account = relationship("Account", foreign_keys=[destination_account_id])
    ledger_entries = relationship("LedgerEntry", back_populates="transaction")
    fraud_alerts = relationship("FraudAlert", back_populates="transaction")

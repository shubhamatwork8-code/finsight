from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RiskSettings(Base):
    __tablename__ = "risk_settings"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    duplicate_window_minutes: Mapped[int] = mapped_column(default=5)
    duplicate_score: Mapped[int] = mapped_column(default=40)
    frequency_threshold: Mapped[int] = mapped_column(default=5)
    frequency_window_minutes: Mapped[int] = mapped_column(default=5)
    frequency_score: Mapped[int] = mapped_column(default=20)
    large_multiplier_medium: Mapped[int] = mapped_column(default=3)
    large_multiplier_high: Mapped[int] = mapped_column(default=5)
    large_score_medium: Mapped[int] = mapped_column(default=25)
    large_score_high: Mapped[int] = mapped_column(default=35)
    unusual_time_score: Mapped[int] = mapped_column(default=10)
    unusual_start_hour: Mapped[int] = mapped_column(default=0)
    unusual_end_hour: Mapped[int] = mapped_column(default=5)
    anomaly_score: Mapped[int] = mapped_column(default=20)
    min_history_count: Mapped[int] = mapped_column(default=3)
    alert_threshold: Mapped[int] = mapped_column(default=30)
    ledger_currency: Mapped[str] = mapped_column(String(3), default="USD")
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

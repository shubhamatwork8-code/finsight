from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.timeutil import utcnow


class AlertReview(Base):
    __tablename__ = "alert_reviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    alert_id: Mapped[str] = mapped_column(ForeignKey("fraud_alerts.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    from_status: Mapped[str] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

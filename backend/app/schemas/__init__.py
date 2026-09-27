from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_type: Literal["CHECKING", "SAVINGS", "OPERATIONS"]
    currency: str = "USD"
    opening_balance: Decimal = Decimal("0")


class TransactionCreate(BaseModel):
    account_id: str
    destination_account_id: str | None = None
    transaction_type: Literal["CREDIT", "DEBIT", "TRANSFER"]
    amount: Decimal
    currency: str = "USD"
    merchant: str
    category: str
    description: str = ""
    timestamp: datetime
    location: str | None = None


class AlertReview(BaseModel):
    status: Literal["UNDER_REVIEW", "RESOLVED", "FALSE_POSITIVE"] = "UNDER_REVIEW"
    resolution_note: str = ""


class AlertUpdate(BaseModel):
    status: Literal["OPEN", "UNDER_REVIEW", "RESOLVED", "FALSE_POSITIVE"] | None = None
    resolution_note: str | None = None


class ReceiptConfirm(BaseModel):
    account_id: str
    transaction_type: Literal["CREDIT", "DEBIT"]
    amount: Decimal
    currency: str = "USD"
    merchant: str
    category: str = "Uncategorized"
    description: str = ""
    timestamp: datetime
    location: str | None = None
    source_filename: str = ""


class RiskSettingsUpdate(BaseModel):
    duplicate_window_minutes: int = Field(ge=1, le=1440)
    duplicate_score: int = Field(ge=0, le=100)
    frequency_threshold: int = Field(ge=2, le=50)
    frequency_window_minutes: int = Field(ge=1, le=1440)
    frequency_score: int = Field(ge=0, le=100)
    large_multiplier_medium: int = Field(ge=2, le=20)
    large_multiplier_high: int = Field(ge=2, le=50)
    large_score_medium: int = Field(ge=0, le=100)
    large_score_high: int = Field(ge=0, le=100)
    unusual_time_score: int = Field(ge=0, le=100)
    unusual_start_hour: int = Field(ge=0, le=23)
    unusual_end_hour: int = Field(ge=1, le=24)
    anomaly_score: int = Field(ge=0, le=100)
    min_history_count: int = Field(ge=1, le=50)
    alert_threshold: int = Field(ge=1, le=100)
    ledger_currency: str = "USD"

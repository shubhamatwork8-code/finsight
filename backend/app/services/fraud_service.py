from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.money import money
from app.services.bootstrap import OPENING_BALANCE_CATEGORY

LOW_MAX = 29
MEDIUM_MAX = 69


@dataclass
class TxView:
    id: str
    amount: Decimal
    merchant: str
    category: str
    occurred_at: datetime


@dataclass
class TriggeredRule:
    code: str
    points: int
    explanation: str

    def as_dict(self) -> dict:
        return {"code": self.code, "points": self.points, "explanation": self.explanation}


@dataclass
class RiskResult:
    score: int
    level: str
    triggered_rules: list[TriggeredRule]
    explanation: str
    recommended_status: str

    @property
    def rules_payload(self) -> list[dict]:
        return [rule.as_dict() for rule in self.triggered_rules]


def risk_level(score: int) -> str:
    if score <= LOW_MAX:
        return "LOW"
    if score <= MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"


def _naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _merchant_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _ratio_text(amount: Decimal, average: Decimal) -> str:
    ratio = (amount / average).quantize(Decimal("0.1"))
    return f"{ratio}"


def _cash(amount: Decimal, currency: str) -> str:
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "INR": "₹",
        "JPY": "¥",
        "AUD": "A$",
        "CAD": "C$",
        "SGD": "S$",
        "CHF": "CHF ",
        "AED": "AED ",
    }
    prefix = symbols.get(currency, f"{currency} ")
    return f"{prefix}{money(amount):,.2f}"


def evaluate_risk(current: TxView, prior: list[TxView], settings, currency: str = "USD") -> RiskResult:
    history = [
        TxView(
            id=item.id,
            amount=item.amount,
            merchant=item.merchant,
            category=item.category,
            occurred_at=_naive(item.occurred_at),
        )
        for item in prior
        if item.id != current.id and item.category != OPENING_BALANCE_CATEGORY
    ]
    current = TxView(
        id=current.id,
        amount=current.amount,
        merchant=current.merchant,
        category=current.category,
        occurred_at=_naive(current.occurred_at),
    )
    rules: list[TriggeredRule] = []
    window = timedelta(minutes=int(settings.duplicate_window_minutes))
    current_merchant = _merchant_key(current.merchant)
    current_amount = money(current.amount)

    for item in history:
        if _merchant_key(item.merchant) != current_merchant:
            continue
        if money(item.amount) != current_amount:
            continue
        if abs(current.occurred_at - item.occurred_at) <= window:
            rules.append(
                TriggeredRule(
                    code="DUPLICATE_TRANSACTION",
                    points=int(settings.duplicate_score),
                    explanation=(
                        f'Duplicate transaction detected for merchant "{current.merchant}" '
                        f"({_cash(current_amount, currency)}) within {int(settings.duplicate_window_minutes)} minutes"
                    ),
                )
            )
            break

    amounts = [money(item.amount) for item in history]
    average = (sum(amounts) / Decimal(len(amounts))) if amounts else None
    enough_history = average is not None and len(amounts) >= int(settings.min_history_count) and average > 0

    if enough_history:
        ratio = current_amount / average
        if ratio >= Decimal(int(settings.large_multiplier_high)):
            rules.append(
                TriggeredRule(
                    code="LARGE_TRANSACTION",
                    points=int(settings.large_score_high),
                    explanation=(
                        f"Amount is {_ratio_text(current_amount, average)}x the account average of {_cash(average, currency)}"
                    ),
                )
            )
        elif ratio >= Decimal(int(settings.large_multiplier_medium)):
            rules.append(
                TriggeredRule(
                    code="LARGE_TRANSACTION",
                    points=int(settings.large_score_medium),
                    explanation=(
                        f"Amount is {_ratio_text(current_amount, average)}x the account average of {_cash(average, currency)}"
                    ),
                )
            )

    freq_window = timedelta(minutes=int(settings.frequency_window_minutes))
    nearby = sum(1 for item in history if abs(current.occurred_at - item.occurred_at) <= freq_window)
    frequency_count = nearby + 1
    if frequency_count >= int(settings.frequency_threshold):
        rules.append(
            TriggeredRule(
                code="HIGH_FREQUENCY",
                points=int(settings.frequency_score),
                explanation=(
                    f"{frequency_count} transactions occurred within {int(settings.frequency_window_minutes)} minutes"
                ),
            )
        )

    hour = current.occurred_at.hour
    if int(settings.unusual_start_hour) <= hour < int(settings.unusual_end_hour):
        night_count = sum(
            1
            for item in history
            if int(settings.unusual_start_hour) <= item.occurred_at.hour < int(settings.unusual_end_hour)
        )
        night_ratio = (night_count / len(history)) if history else 0
        if len(history) < 8 or night_ratio < 0.25:
            rules.append(
                TriggeredRule(
                    code="UNUSUAL_TIME",
                    points=int(settings.unusual_time_score),
                    explanation=(
                        f"Transaction time {current.occurred_at.strftime('%H:%M')} UTC is outside this account's usual hours"
                    ),
                )
            )

    if enough_history:
        reasons = []
        mean = average
        variance = sum((amount - mean) ** 2 for amount in amounts) / Decimal(len(amounts))
        deviation = variance.sqrt()
        if deviation > 0 and current_amount > mean + (Decimal("2") * deviation):
            reasons.append("amount is more than 2 standard deviations above the account mean")
        known = {_merchant_key(item.merchant) for item in history}
        if current_merchant not in known and current_amount >= mean * 2:
            reasons.append("merchant is new for this account and the amount is at least 2x the average")
        if reasons:
            rules.append(
                TriggeredRule(
                    code="HISTORICAL_ANOMALY",
                    points=int(settings.anomaly_score),
                    explanation="Historical behavior anomaly: " + "; ".join(reasons),
                )
            )

    score = min(100, sum(rule.points for rule in rules))
    level = risk_level(score)
    if rules:
        sentences = []
        for rule in rules:
            text = rule.explanation.strip()
            if not text.endswith("."):
                text += "."
            sentences.append(text)
        explanation = "Transaction flagged for review because " + " ".join(sentences)
    else:
        explanation = "No material risk signals were triggered for this transaction."
    status = "POSTED" if level == "LOW" else "UNDER_REVIEW"
    return RiskResult(
        score=score,
        level=level,
        triggered_rules=rules,
        explanation=explanation,
        recommended_status=status,
    )


def rule_summary(rules: list[dict] | list) -> str:
    labels = {
        "DUPLICATE_TRANSACTION": "Duplicate transaction",
        "LARGE_TRANSACTION": "Large transaction",
        "HIGH_FREQUENCY": "Velocity burst",
        "UNUSUAL_TIME": "Unusual time",
        "HISTORICAL_ANOMALY": "Historical anomaly",
    }
    names = []
    for rule in rules:
        code = rule["code"] if isinstance(rule, dict) else rule.code
        names.append(labels.get(code, code.replace("_", " ").title()))
    return " + ".join(names)


def primary_rule(result: RiskResult) -> str:
    if not result.triggered_rules:
        return "NONE"
    return max(result.triggered_rules, key=lambda rule: rule.points).code

from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sklearn.metrics import average_precision_score

from app.services.fraud_service import TxView, evaluate_risk, risk_level
from app.services.ml_service import anomaly_score

_METRICS = ("precision", "recall", "f1", "pr_auc", "false_positive_rate")


def compare_models() -> dict:
    settings = SimpleNamespace(
        duplicate_window_minutes=5,
        duplicate_score=40,
        frequency_threshold=5,
        frequency_window_minutes=5,
        frequency_score=20,
        large_multiplier_medium=3,
        large_multiplier_high=5,
        large_score_medium=25,
        large_score_high=35,
        unusual_time_score=10,
        unusual_start_hour=0,
        unusual_end_hour=5,
        anomaly_score=20,
        min_history_count=3,
        alert_threshold=30,
    )
    labeled = _benchmark_cases()
    rows = []
    prior: list[TxView] = []
    for case in labeled:
        current = case["view"]
        result = evaluate_risk(current, prior, settings, currency="USD")
        model = anomaly_score(current, prior, result.score)
        hybrid = min(100, int(round((0.7 * result.score) + (0.3 * model))))
        rows.append(
            {
                "label": case["label"],
                "rules": result.score,
                "model": model,
                "hybrid": hybrid,
            }
        )
        prior.append(current)
    return {
        "rules": _metrics(rows, "rules"),
        "model": _metrics(rows, "model"),
        "hybrid": _metrics(rows, "hybrid"),
        "threshold": 30,
        "note": "These figures are scored on a fixed benchmark of ordinary spend and scripted fraud cases. They are separate from the signed-in ledger.",
    }


def _metrics(rows: list[dict], key: str) -> dict:
    labels = [row["label"] for row in rows]
    scores = [row[key] / 100 for row in rows]
    predicted = [1 if row[key] >= 30 else 0 for row in rows]
    true_positive = sum(1 for label, guess in zip(labels, predicted) if label == 1 and guess == 1)
    false_positive = sum(1 for label, guess in zip(labels, predicted) if label == 0 and guess == 1)
    false_negative = sum(1 for label, guess in zip(labels, predicted) if label == 1 and guess == 0)
    true_negative = sum(1 for label, guess in zip(labels, predicted) if label == 0 and guess == 0)
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    false_positive_rate = false_positive / (false_positive + true_negative) if false_positive + true_negative else 0.0
    try:
        pr_auc = float(average_precision_score(labels, scores))
    except ValueError:
        pr_auc = 0.0
    values = {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "pr_auc": pr_auc,
        "false_positive_rate": false_positive_rate,
    }
    return {name: round(values[name], 2) for name in _METRICS}


def _benchmark_cases() -> list[dict]:
    start = datetime(2026, 9, 1, 11, 0)
    cases = []
    for index in range(12):
        cases.append(_case(f"N{index}", Decimal("48.00") + Decimal(index), "Blue Bottle Coffee", start + timedelta(days=index), 0))
    cases.append(_case("F-dup", Decimal("59.00"), "Blue Bottle Coffee", start + timedelta(days=11, minutes=2), 1))
    cases.append(_case("F-large", Decimal("900.00"), "Apex Equipment", start + timedelta(days=12, hours=1), 1))
    cases.append(_case("F-night", Decimal("70.00"), "Night Kiosk", start.replace(hour=2) + timedelta(days=13), 1))
    burst = start + timedelta(days=14, hours=2)
    for index in range(5):
        label = 1 if index == 4 else 0
        cases.append(_case(f"B{index}", Decimal("22.00"), f"Parts {index}", burst + timedelta(minutes=index), label))
    return cases


def _case(name: str, amount: Decimal, merchant: str, moment: datetime, label: int) -> dict:
    return {
        "label": label,
        "view": TxView(id=name, amount=amount, merchant=merchant, category="Shopping", occurred_at=moment),
    }


def hybrid_level(score: int) -> str:
    return risk_level(score)

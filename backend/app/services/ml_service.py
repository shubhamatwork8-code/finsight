from datetime import timedelta

import numpy as np
from sklearn.ensemble import IsolationForest

from app.services.fraud_service import TxView, _naive


def anomaly_score(current: TxView, prior: list[TxView], fallback: int) -> int:
    history = [item for item in prior if item.category != "OPENING_BALANCE"]
    if len(history) < 8:
        return fallback
    rows = [_features(item, history) for item in history]
    try:
        model = IsolationForest(n_estimators=40, contamination=0.08, random_state=42)
        model.fit(np.array(rows, dtype=float))
        decision = float(model.decision_function(np.array([_features(current, history)], dtype=float))[0])
    except ValueError:
        return fallback
    scaled = int(round(50 - (decision * 80)))
    return max(0, min(100, scaled))


def _features(item: TxView, history: list[TxView]) -> list[float]:
    moment = _naive(item.occurred_at)
    window = [
        other
        for other in history
        if other.id != item.id and abs((_naive(other.occurred_at) - moment).total_seconds()) <= timedelta(minutes=5).total_seconds()
    ]
    known = {other.merchant.casefold() for other in history if other.id != item.id}
    return [
        float(item.amount),
        float(moment.hour),
        0.0 if item.merchant.casefold() in known else 1.0,
        float(len(window)),
    ]

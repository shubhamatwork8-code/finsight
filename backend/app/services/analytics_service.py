from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.money import money
from app.models import Account, AuditLog, FraudAlert, Transaction
from app.services.bootstrap import OPENING_BALANCE_CATEGORY
from app.services.context import current_user_id
from app.services.tenancy import owned_customer_ids, visible_transactions


def _customer_transactions(db: Session):
    return visible_transactions(db).filter(Transaction.category != OPENING_BALANCE_CATEGORY)


def _customer_accounts(db: Session):
    ids = owned_customer_ids(db)
    query = db.query(Account).filter(Account.account_type != "SYSTEM")
    if not ids:
        return query.filter(Account.id == "")
    return query.filter(Account.id.in_(ids))


def _alerts(db: Session):
    ids = owned_customer_ids(db)
    query = db.query(FraudAlert)
    if not ids:
        return query.filter(FraudAlert.id == "")
    return query.filter(FraudAlert.account_id.in_(ids))


def dashboard_summary(db: Session) -> dict:
    accounts = _customer_accounts(db).all()
    active = [account for account in accounts if account.status == "ACTIVE"]
    transactions = _customer_transactions(db).all()
    open_alerts = _alerts(db).filter(FraudAlert.status == "OPEN").all()
    volume = defaultdict(lambda: Decimal("0.00"))
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for transaction in transactions:
        day = transaction.occurred_at.date().isoformat()
        volume[day] = money(volume[day] + transaction.amount)
        risk_counts[transaction.risk_level] = risk_counts.get(transaction.risk_level, 0) + 1
    recent = (
        _customer_transactions(db)
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .limit(8)
        .all()
    )
    queue = (
        _alerts(db)
        .filter(FraudAlert.status.in_(["OPEN", "UNDER_REVIEW"]))
        .order_by(FraudAlert.risk_score.desc(), FraudAlert.created_at.desc())
        .limit(6)
        .all()
    )
    return {
        "total_balance": money(sum((money(account.balance) for account in active), Decimal("0"))),
        "active_accounts": len(active),
        "transaction_volume": money(sum((money(item.amount) for item in transactions), Decimal("0"))),
        "transaction_count": len(transactions),
        "open_alerts": len(open_alerts),
        "high_risk_alerts": sum(1 for alert in open_alerts if alert.risk_level == "HIGH"),
        "recent_transactions": recent,
        "attention_queue": queue,
        "volume_series": [{"date": day, "amount": volume[day]} for day in sorted(volume)],
        "risk_distribution": risk_counts,
    }


def transaction_analytics(db: Session) -> dict:
    transactions = _customer_transactions(db).all()
    volume = defaultdict(lambda: Decimal("0.00"))
    by_type = defaultdict(lambda: Decimal("0.00"))
    by_category = defaultdict(lambda: Decimal("0.00"))
    for transaction in transactions:
        day = transaction.occurred_at.date().isoformat()
        volume[day] = money(volume[day] + transaction.amount)
        by_type[transaction.transaction_type] = money(by_type[transaction.transaction_type] + transaction.amount)
        by_category[transaction.category] = money(by_category[transaction.category] + transaction.amount)
    return {
        "volume_over_time": [{"date": day, "amount": volume[day]} for day in sorted(volume)],
        "credit_vs_debit": [
            {"type": kind, "amount": by_type.get(kind, Decimal("0.00"))}
            for kind in ("CREDIT", "DEBIT", "TRANSFER")
        ],
        "category_breakdown": [
            {"category": name, "amount": amount}
            for name, amount in sorted(by_category.items(), key=lambda item: item[1], reverse=True)
        ],
    }


def risk_analytics(db: Session) -> dict:
    transactions = _customer_transactions(db).all()
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    alerts = _alerts(db).all()
    by_day = defaultdict(int)
    fraud_category = defaultdict(lambda: Decimal("0.00"))
    histogram = {f"{start}-{start + 9 if start < 90 else 100}": 0 for start in range(0, 100, 10)}
    rule_counts = defaultdict(int)
    for transaction in transactions:
        counts[transaction.risk_level] = counts.get(transaction.risk_level, 0) + 1
        if transaction.risk_level != "LOW":
            fraud_category[transaction.category] = money(fraud_category[transaction.category] + transaction.amount)
        bucket_start = min(90, (int(transaction.risk_score or 0) // 10) * 10)
        bucket = f"{bucket_start}-{bucket_start + 9 if bucket_start < 90 else 100}"
        histogram[bucket] = histogram.get(bucket, 0) + 1
        for rule in transaction.triggered_rules or []:
            code = rule.get("code") if isinstance(rule, dict) else None
            if code:
                rule_counts[code] += 1
    for alert in alerts:
        by_day[alert.created_at.date().isoformat()] += 1
    from app.services.model_comparison import compare_models

    return {
        "risk_distribution": [{"level": level, "count": counts.get(level, 0)} for level in ("LOW", "MEDIUM", "HIGH")],
        "alerts_over_time": [{"date": day, "count": by_day[day]} for day in sorted(by_day)],
        "fraud_by_category": [
            {"category": name, "amount": amount}
            for name, amount in sorted(fraud_category.items(), key=lambda item: item[1], reverse=True)
        ],
        "score_histogram": [{"bucket": bucket, "count": histogram[bucket]} for bucket in histogram],
        "rule_frequency": [
            {"rule": name, "count": count}
            for name, count in sorted(rule_counts.items(), key=lambda item: item[1], reverse=True)
        ],
        "model_comparison": compare_models(),
    }


def overview(db: Session) -> dict:
    summary = dashboard_summary(db)
    return {
        "accounts": summary["active_accounts"],
        "total_balance": summary["total_balance"],
        "transaction_count": summary["transaction_count"],
        "transaction_volume": summary["transaction_volume"],
        "open_alerts": summary["open_alerts"],
        "audit_events": db.query(AuditLog).filter(AuditLog.user_id == current_user_id.get()).count(),
    }

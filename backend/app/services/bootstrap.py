from app.core.config import get_settings
from app.models import Account, AuditLog, RiskSettings, User
from app.services.security import hash_password

DEMO_USER_ID = "USR-DEMO"
SETTLEMENT_ACCOUNT_ID = "ACC-SETTLEMENT"
SETTINGS_ID = "default"
OPENING_BALANCE_CATEGORY = "OPENING_BALANCE"


def provision_workspace(db, user: User) -> None:
    settlement_id = SETTLEMENT_ACCOUNT_ID if user.id == DEMO_USER_ID else f"SET-{user.id}"
    existing_settlement = (
        db.query(Account).filter(Account.user_id == user.id, Account.account_type == "SYSTEM").one_or_none()
    )
    if existing_settlement is None:
        db.add(
            Account(
                id=settlement_id,
                user_id=user.id,
                name="External Settlement",
                account_number="SYSTEM0000",
                ifsc_code="SYS000",
                account_type="SYSTEM",
                currency="USD",
                balance=0,
                status="ACTIVE",
            )
        )
    settings = db.query(RiskSettings).filter(RiskSettings.user_id == user.id).one_or_none()
    if settings is None and user.id == DEMO_USER_ID:
        settings = db.get(RiskSettings, SETTINGS_ID)
        if settings is not None and settings.user_id is None:
            settings.user_id = user.id
    if settings is None:
        db.add(RiskSettings(id=SETTINGS_ID if user.id == DEMO_USER_ID else user.id, user_id=user.id))


def bootstrap(db) -> None:
    user = db.get(User, DEMO_USER_ID)
    if user is None:
        user = User(
            id=DEMO_USER_ID,
            email="demo@finsight.local",
            full_name="Avery Chen",
            password_hash=hash_password(get_settings().demo_password),
        )
        db.add(user)
        db.flush()
    elif not user.password_hash:
        user.password_hash = hash_password(get_settings().demo_password)
    provision_workspace(db, user)
    db.query(AuditLog).filter(AuditLog.user_id.is_(None)).update(
        {AuditLog.user_id: DEMO_USER_ID}, synchronize_session=False
    )
    db.commit()

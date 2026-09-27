from fastapi import APIRouter

from app.api import accounts, analytics, audit, auth, dashboard, fraud, health, ledger, settings, transactions

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(transactions.router)
api_router.include_router(ledger.router)
api_router.include_router(fraud.router)
api_router.include_router(analytics.router)
api_router.include_router(dashboard.router)
api_router.include_router(audit.router)
api_router.include_router(settings.router)

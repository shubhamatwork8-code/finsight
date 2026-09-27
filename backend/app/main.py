import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.errors import AppError
from app.services.bootstrap import bootstrap
from app.services.context import current_user_id
from app.services.security import read_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.database_url.startswith("sqlite:///./"):
        os.makedirs("data", exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        bootstrap(db)
        if settings.seed_on_startup:
            from app.seed import seed_demo_if_empty

            seed_demo_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title="FinSight", version="1.0.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.middleware("http")
async def bind_current_user(request: Request, call_next):
    header = request.headers.get("authorization")
    token = None
    if header and header.lower().startswith("bearer "):
        try:
            token = current_user_id.set(read_token(header.split(" ", 1)[1].strip()))
        except AppError:
            token = None
    try:
        return await call_next(request)
    finally:
        if token is not None:
            current_user_id.reset(token)


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.code, "message": exc.message})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    parts = []
    for error in exc.errors():
        location = ".".join(str(item) for item in error.get("loc", []) if item not in {"body", "query"})
        message = error.get("msg", "Invalid value")
        parts.append(f"{location}: {message}" if location else message)
    return JSONResponse(
        status_code=422,
        content={"error": "INVALID_REQUEST", "message": "; ".join(parts) or "Request data is invalid"},
    )


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"error": "DATABASE_ERROR", "message": "The database operation could not be completed."},
    )


@app.get("/")
def root():
    return {"name": "FinSight", "docs": "/docs", "health": "/api/health"}

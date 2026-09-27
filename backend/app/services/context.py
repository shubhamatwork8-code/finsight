import contextvars

current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id", default="USR-DEMO")

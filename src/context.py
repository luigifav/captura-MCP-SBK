from contextvars import ContextVar

login_var: ContextVar[str] = ContextVar("login", default="")
senha_var: ContextVar[str] = ContextVar("senha", default="")

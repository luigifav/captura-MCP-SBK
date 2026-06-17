import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.context import login_var, senha_var
from src.tools import download, fila, health, movimentos, pesquisas

mcp = FastMCP(
    "captura-mcp-sbk",
    instructions=(
        "Servidor MCP para a API de Captura SBK. "
        "Expõe ferramentas para consultar e interagir com os endpoints de captura. "
        "Credenciais são fornecidas via headers X-Captura-Login e X-Captura-Senha."
    ),
)

health.register(mcp)
fila.register(mcp)
download.register(mcp)
movimentos.register(mcp)
pesquisas.register(mcp)


class CredentialMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        login = request.headers.get("x-captura-login", os.getenv("CAPTURA_LOGIN", ""))
        senha = request.headers.get("x-captura-senha", os.getenv("CAPTURA_SENHA", ""))
        t_login = login_var.set(login)
        t_senha = senha_var.set(senha)
        try:
            return await call_next(request)
        finally:
            login_var.reset(t_login)
            senha_var.reset(t_senha)


mcp.add_middleware(Middleware(CredentialMiddleware))


def run() -> None:
    port = os.getenv("PORT")
    if port:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run()

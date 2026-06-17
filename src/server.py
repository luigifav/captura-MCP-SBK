import os
import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import download, fila, health, movimentos, pesquisas

mcp = FastMCP(
    "captura-mcp-sbk",
    instructions=(
        "Servidor MCP para a API de Captura SBK. "
        "Expõe ferramentas para consultar e interagir com os endpoints de captura, "
        "incluindo verificação de disponibilidade (captura_health). "
        "Autenticação é feita via login/senha configurados no .env, com cache de token."
    ),
)

health.register(mcp)
fila.register(mcp)
download.register(mcp)
movimentos.register(mcp)
pesquisas.register(mcp)


def run() -> None:
    port = os.getenv("PORT")
    if port:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run()

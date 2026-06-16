from fastmcp import FastMCP

import sys
from pathlib import Path

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


if __name__ == "__main__":
    mcp.run()

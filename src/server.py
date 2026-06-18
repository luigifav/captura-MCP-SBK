import os
import sys
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import download, fila, health, movimentos, pesquisas

mcp = FastMCP(
    "captura-mcp-sbk",
    instructions=(
        "Servidor MCP para a API de Captura SBK. "
        "Expõe ferramentas para consultar e interagir com os endpoints de captura."
    ),
)

health.register(mcp)
fila.register(mcp)
download.register(mcp)
movimentos.register(mcp)
pesquisas.register(mcp)


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/debug/connectivity", methods=["GET"])
async def debug_connectivity(request: Request) -> JSONResponse:
    import socket
    import httpx
    from src import config

    results = {}

    s = socket.socket()
    s.settimeout(5)
    tcp_result = s.connect_ex(("apisbk.sbk.com.br", 443))
    s.close()
    results["tcp_443"] = "open" if tcp_result == 0 else f"blocked (err {tcp_result})"

    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            resp = await client.get(f"{config.BASE_URL}/v1/api/auth/login")
            results["http_get"] = resp.status_code
    except Exception as exc:
        results["http_get"] = str(exc)

    return JSONResponse(results)


def run() -> None:
    port = os.getenv("PORT")
    if port:
        server_url = os.getenv("SERVER_URL", f"http://0.0.0.0:{port}")
        from src.oauth import SBKOAuthProvider
        mcp.auth = SBKOAuthProvider(base_url=server_url)
        mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    run()

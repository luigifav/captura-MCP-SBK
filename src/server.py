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
        "Expõe ferramentas para consultar e interagir com os endpoints de captura. "
        "Sempre que uma tool retornar o campo portal_sbk, inclua o link na sua resposta ao usuário."
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


@mcp.custom_route("/debug/test-api", methods=["GET"])
async def test_api(request: Request) -> JSONResponse:
    import httpx
    from src import config
    url = f"{config.BASE_URL}/v1/api/auth/login"
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=False) as http:
            resp = await http.post(url, json={"login": "_test_", "senha": "_test_"})
            return JSONResponse({"ok": True, "url": url, "status": resp.status_code, "body": resp.text[:300]})
    except Exception as exc:
        return JSONResponse({"ok": False, "url": url, "error": type(exc).__name__, "detail": str(exc)})


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

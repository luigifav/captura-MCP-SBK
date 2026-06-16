import httpx
from fastmcp import FastMCP

from src import config


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def captura_health() -> dict:
        """Verifica disponibilidade da API de Captura SBK. Sem autenticação."""
        url = f"{config.BASE_URL}/v1/api/health"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
            status = "ok" if 200 <= resp.status_code < 300 else "degraded"
            return {"status": status, "http_status": resp.status_code}
        except httpx.HTTPError:
            return {"status": "degraded", "http_status": 0}

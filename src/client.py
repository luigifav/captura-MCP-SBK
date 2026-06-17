from typing import Any

import httpx

from src import config
from src.auth import token_manager


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    url = f"{config.BASE_URL}{path}"

    async def _do(token: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            return await client.request(
                method, url, params=params, json=json, headers=headers
            )

    token = await token_manager.get_token()
    resp = await _do(token)

    if resp.status_code == 401:
        token_manager.invalidate()
        token = await token_manager.get_token()
        resp = await _do(token)

    if resp.status_code == 403:
        raise PermissionError(
            f"Acesso negado (403) para o usuário '{config.LOGIN}' em {method} {path}. "
            "Verifique permissões na API de Captura SBK."
        )

    resp.raise_for_status()
    return resp.json()


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    return await _request("GET", path, params=params)


async def post(path: str, body: dict[str, Any] | None = None) -> Any:
    return await _request("POST", path, json=body)

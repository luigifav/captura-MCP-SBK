import os
from typing import Any

import httpx

from src import auth, config
from src.context import login_var, senha_var


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
) -> Any:
    login = login_var.get() or os.getenv("CAPTURA_LOGIN", "")
    senha = senha_var.get() or os.getenv("CAPTURA_SENHA", "")

    if not login or not senha:
        raise RuntimeError(
            "Credenciais não configuradas. "
            "Informe X-Captura-Login e X-Captura-Senha nos headers da conexão MCP."
        )

    url = f"{config.BASE_URL}{path}"

    async def _do(token: str) -> httpx.Response:
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            return await client.request(
                method, url, params=params, json=json, headers=headers
            )

    token = await auth.get_token(login, senha)
    resp = await _do(token)

    if resp.status_code == 401:
        auth.invalidate(login, senha)
        token = await auth.get_token(login, senha)
        resp = await _do(token)

    if resp.status_code == 403:
        raise PermissionError(
            f"Acesso negado (403) para o usuário '{login}' em {method} {path}. "
            "Verifique permissões na API de Captura SBK."
        )

    resp.raise_for_status()
    return resp.json()


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    return await _request("GET", path, params=params)


async def post(path: str, body: dict[str, Any] | None = None) -> Any:
    return await _request("POST", path, json=body)

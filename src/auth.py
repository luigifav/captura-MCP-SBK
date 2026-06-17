import asyncio
import time

import httpx

from src import config

TTL_SECONDS = 55 * 60

_cache: dict[tuple[str, str], tuple[str, float]] = {}
_locks: dict[tuple[str, str], asyncio.Lock] = {}
_locks_meta = asyncio.Lock()


async def get_token(login: str, senha: str) -> str:
    key = (login, senha)

    async with _locks_meta:
        if key not in _locks:
            _locks[key] = asyncio.Lock()

    async with _locks[key]:
        cached = _cache.get(key)
        if cached:
            token, expires_at = cached
            if time.monotonic() < expires_at:
                return token

        url = f"{config.BASE_URL}/v1/api/auth/login"
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.post(url, json={"login": login, "senha": senha})
            resp.raise_for_status()
            data = resp.json()

        token = (
            data.get("token_acesso")
            or data.get("token")
            or data.get("access_token")
            or data.get("accessToken")
        )
        if not token:
            raise RuntimeError(f"Resposta de login não contém token: {data}")

        _cache[key] = (token, time.monotonic() + TTL_SECONDS)
        return token


def invalidate(login: str, senha: str) -> None:
    _cache.pop((login, senha), None)

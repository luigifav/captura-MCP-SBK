import asyncio
import time

import httpx

from src import config

TTL_SECONDS = 55 * 60


class TokenManager:
    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        async with self._lock:
            if self._token and time.monotonic() < self._expires_at:
                return self._token
            await self._refresh()
            assert self._token is not None
            return self._token

    async def _refresh(self) -> None:
        url = f"{config.BASE_URL}/v1/api/auth/login"
        payload = {"login": config.LOGIN, "senha": config.SENHA}
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            resp = await client.post(url, json=payload)
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
        self._token = token
        self._expires_at = time.monotonic() + TTL_SECONDS

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0


token_manager = TokenManager()

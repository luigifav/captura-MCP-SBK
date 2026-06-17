import os
import secrets
import time
from html import escape

import httpx
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from fastmcp.server.auth.providers.in_memory import (
    DEFAULT_AUTH_CODE_EXPIRY_SECONDS,
    InMemoryOAuthProvider,
)
from mcp.server.auth.settings import ClientRegistrationOptions
from src import config
from src.context import login_var, senha_var

_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Login - Captura SBK</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 380px; margin: 80px auto; padding: 24px; }}
  h2 {{ margin-bottom: 4px; }}
  p {{ color: #555; margin-top: 0; }}
  label {{ font-size: 14px; font-weight: bold; }}
  input {{ display: block; width: 100%; padding: 8px; margin: 6px 0 16px;
           box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }}
  button {{ background: #0a6; color: white; border: none; padding: 10px;
             cursor: pointer; width: 100%; border-radius: 4px; font-size: 15px; }}
  button:hover {{ background: #085; }}
  .err {{ color: #c00; background: #fee; border: 1px solid #fcc;
          padding: 8px 12px; border-radius: 4px; margin-bottom: 16px; }}
</style>
</head>
<body>
<h2>Captura SBK</h2>
<p>Entre com suas credenciais para autorizar o acesso.</p>
{error}
<form method="post">
  <input type="hidden" name="t" value="{token}">
  <label>Login</label>
  <input type="text" name="login" required autofocus autocomplete="username">
  <label>Senha</label>
  <input type="password" name="senha" required autocomplete="current-password">
  <button type="submit">Entrar</button>
</form>
</body>
</html>"""


class CredentialExtractorMiddleware:
    """Pure ASGI middleware: extracts SBK credentials from OAuth token or custom headers."""

    def __init__(self, app, provider: "SBKOAuthProvider"):
        self.app = app
        self.provider = provider

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope["headers"]}

        login = ""
        senha = ""

        # 1. OAuth bearer token
        auth_header = headers.get(b"authorization", b"").decode()
        if auth_header.startswith("Bearer "):
            token_str = auth_header[7:]
            creds = self.provider.get_credentials(token_str)
            if creds:
                login, senha = creds

        # 2. Custom headers (Claude Desktop)
        if not login:
            login = headers.get(b"x-captura-login", b"").decode()
            senha = headers.get(b"x-captura-senha", b"").decode()

        # 3. Env vars (local HTTP testing)
        if not login:
            login = os.getenv("CAPTURA_LOGIN", "")
            senha = os.getenv("CAPTURA_SENHA", "")

        t_login = login_var.set(login)
        t_senha = senha_var.set(senha)
        try:
            await self.app(scope, receive, send)
        finally:
            login_var.reset(t_login)
            senha_var.reset(t_senha)


class SBKOAuthProvider(InMemoryOAuthProvider):
    """OAuth provider that validates credentials against the SBK API."""

    def __init__(self, base_url: str):
        super().__init__(
            base_url=base_url,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )
        self._pending: dict[str, tuple] = {}
        self._credentials_by_code: dict[str, tuple[str, str]] = {}
        self._credentials_by_token: dict[str, tuple[str, str]] = {}

    # --- OAuth flow overrides ---

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        temp = secrets.token_urlsafe(32)
        self._pending[temp] = (client, params)
        base = str(self.base_url).rstrip("/")
        return f"{base}/login?t={temp}"

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        credentials = self._credentials_by_code.pop(authorization_code.code, None)
        token = await super().exchange_authorization_code(client, authorization_code)
        if credentials:
            self._credentials_by_token[token.access_token] = credentials
        return token

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        old_access = self._refresh_to_access_map.get(refresh_token.token)
        credentials = self._credentials_by_token.get(old_access) if old_access else None
        token = await super().exchange_refresh_token(client, refresh_token, scopes)
        if credentials:
            if old_access:
                self._credentials_by_token.pop(old_access, None)
            self._credentials_by_token[token.access_token] = credentials
        return token

    async def revoke_token(self, token) -> None:
        from mcp.server.auth.provider import AccessToken
        if isinstance(token, AccessToken):
            self._credentials_by_token.pop(token.token, None)
        await super().revoke_token(token)

    # --- Credential lookup ---

    def get_credentials(self, access_token: str) -> tuple[str, str] | None:
        return self._credentials_by_token.get(access_token)

    # --- HTTP middleware (includes credential extractor) ---

    def get_middleware(self) -> list:
        middlewares = super().get_middleware()
        middlewares.append(Middleware(CredentialExtractorMiddleware, provider=self))
        return middlewares

    # --- Login page routes ---

    def get_routes(self, mcp_path=None):
        from starlette.routing import Route
        routes = super().get_routes(mcp_path)
        routes.append(Route("/login", endpoint=self._login_get, methods=["GET"]))
        routes.append(Route("/login", endpoint=self._login_post, methods=["POST"]))
        return routes

    async def _login_get(self, request: Request) -> HTMLResponse:
        temp = request.query_params.get("t", "")
        if not temp or temp not in self._pending:
            return HTMLResponse("Link inválido ou expirado.", status_code=400)
        return HTMLResponse(_LOGIN_HTML.format(token=escape(temp), error=""))

    async def _login_post(self, request: Request) -> HTMLResponse | RedirectResponse:
        form = await request.form()
        temp = str(form.get("t") or request.query_params.get("t", ""))
        login = str(form.get("login", "")).strip()
        senha = str(form.get("senha", ""))

        if not temp:
            return HTMLResponse("Token ausente.", status_code=400)

        redirect_uri, error = await self._complete_login(temp, login, senha)
        if error:
            error_html = f'<div class="err">{escape(error)}</div>'
            return HTMLResponse(
                _LOGIN_HTML.format(token=escape(temp), error=error_html),
                status_code=400,
            )
        return RedirectResponse(redirect_uri, status_code=302)

    async def _complete_login(
        self, temp_token: str, login: str, senha: str
    ) -> tuple[str, str | None]:
        """Validate SBK creds, generate auth code, return (redirect_uri, error_msg)."""
        entry = self._pending.get(temp_token)
        if entry is None:
            return ("", "Link inválido ou expirado.")

        client, params = entry

        # Validate against SBK API
        url = f"{config.BASE_URL}/v1/api/auth/login"
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as http:
                resp = await http.post(url, json={"login": login, "senha": senha})
                if resp.status_code in (401, 403):
                    return ("", "Login ou senha inválidos.")
                resp.raise_for_status()
        except httpx.HTTPStatusError:
            return ("", "Login ou senha inválidos.")
        except Exception as exc:
            return ("", f"Erro ao contatar a API: {exc}")

        # Success: consume pending entry and create auth code
        self._pending.pop(temp_token, None)

        code_value = secrets.token_urlsafe(32)
        expires_at = time.time() + DEFAULT_AUTH_CODE_EXPIRY_SECONDS

        scopes_list = list(params.scopes or [])
        if client.scope:
            allowed = set(client.scope.split())
            scopes_list = [s for s in scopes_list if s in allowed]

        if client.client_id is None:
            return ("", "Client ID inválido.")

        auth_code = AuthorizationCode(
            code=code_value,
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            scopes=scopes_list,
            expires_at=expires_at,
            code_challenge=params.code_challenge,
        )
        self.auth_codes[code_value] = auth_code
        self._credentials_by_code[code_value] = (login, senha)

        return (
            construct_redirect_uri(
                str(params.redirect_uri), code=code_value, state=params.state
            ),
            None,
        )

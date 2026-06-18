import logging
import os
import secrets
import time
from html import escape

import httpx

logger = logging.getLogger(__name__)
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
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: system-ui, -apple-system, Arial, sans-serif;
    background: #F0F4F1;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .card {{
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.10);
    width: 100%;
    max-width: 400px;
    overflow: hidden;
  }}
  .card-header {{
    background: #00A651;
    padding: 28px 32px 24px;
    text-align: center;
  }}
  .card-header svg {{
    display: block;
    margin: 0 auto 12px;
  }}
  .card-header h1 {{
    color: #fff;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: 0.3px;
  }}
  .card-header p {{
    color: rgba(255,255,255,0.85);
    font-size: 13px;
    margin-top: 4px;
  }}
  .card-body {{
    padding: 28px 32px 32px;
  }}
  .hint {{
    background: #EAF5F0;
    border-left: 3px solid #00A651;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 13px;
    color: #1A5C35;
    margin-bottom: 22px;
    line-height: 1.5;
  }}
  .field {{
    margin-bottom: 18px;
  }}
  label {{
    display: block;
    font-size: 13px;
    font-weight: 600;
    color: #374151;
    margin-bottom: 6px;
  }}
  input[type="text"],
  input[type="password"] {{
    display: block;
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #D1D5DB;
    border-radius: 6px;
    font-size: 14px;
    color: #1A1A1A;
    transition: border-color 0.15s, box-shadow 0.15s;
    background: #fff;
  }}
  input[type="text"]:focus,
  input[type="password"]:focus {{
    outline: none;
    border-color: #00A651;
    box-shadow: 0 0 0 3px rgba(0,166,81,0.15);
  }}
  button {{
    display: block;
    width: 100%;
    padding: 11px;
    background: #00A651;
    color: #fff;
    border: none;
    border-radius: 6px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    margin-top: 8px;
    transition: background 0.15s;
    letter-spacing: 0.2px;
  }}
  button:hover {{ background: #008C44; }}
  button:active {{ background: #007A3C; }}
  .err {{
    color: #991B1B;
    background: #FEF2F2;
    border: 1px solid #FECACA;
    padding: 10px 14px;
    border-radius: 6px;
    font-size: 13px;
    margin-bottom: 18px;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="card-header">
    <svg width="44" height="44" viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="22" cy="22" r="22" fill="rgba(255,255,255,0.18)"/>
      <text x="22" y="28" text-anchor="middle" font-family="system-ui,-apple-system,Arial,sans-serif" font-size="18" font-weight="700" fill="#fff">SBK</text>
    </svg>
    <h1>Captura SBK</h1>
    <p>Autorize o acesso com suas credenciais.</p>
  </div>
  <div class="card-body">
    <div class="hint">
      Use o mesmo login e senha do <strong>Portal de Movimentações SBK</strong>.
    </div>
    {error}
    <form method="post">
      <input type="hidden" name="t" value="{token}">
      <div class="field">
        <label for="login">Login</label>
        <input type="text" id="login" name="login" required autofocus autocomplete="username">
      </div>
      <div class="field">
        <label for="senha">Senha</label>
        <input type="password" id="senha" name="senha" required autocomplete="current-password">
      </div>
      <button type="submit">Entrar</button>
    </form>
  </div>
</div>
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
        logger.info("SBK login attempt: url=%s login=%s", url, login)
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=False) as http:
                resp = await http.post(url, json={"login": login, "senha": senha})
                logger.info("SBK login response status=%s body=%s", resp.status_code, resp.text[:500])
                if resp.status_code in (401, 403):
                    return ("", "Login ou senha inválidos.")
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.exception("SBK login HTTP error: status=%s body=%s", exc.response.status_code, exc.response.text[:500])
            return ("", "Login ou senha inválidos.")
        except Exception as exc:
            logger.exception("SBK login transport error: %r", exc)
            return ("", f"Erro ao contatar a API: {type(exc).__name__}: {exc}")

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

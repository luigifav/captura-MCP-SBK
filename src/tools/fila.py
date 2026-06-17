from typing import Any

from fastmcp import FastMCP

from src import client
from src.utils import _paginar


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def captura_listar_disponiveis(
        paginar_tudo: bool = False,
        cursor: int | None = None,
        limite_paginas: int = 10,
    ) -> dict[str, Any]:
        """Lista processos disponíveis na fila de captura (limitado aos últimos 30 dias).

        Quando paginar_tudo=False, faz uma única chamada e retorna o cursor para a
        próxima página em proximo_cursor (ha_mais indica se há mais dados).
        Quando paginar_tudo=True, itera o cursor até esgotar ou atingir limite_paginas.
        """
        return await _paginar(
            "/v1/api/fila/disponiveis", paginar_tudo, cursor, limite_paginas
        )

    @mcp.tool()
    async def captura_listar_todos(
        paginar_tudo: bool = False,
        cursor: int | None = None,
        limite_paginas: int = 10,
    ) -> dict[str, Any]:
        """Lista todos os processos da fila de captura.

        Processos com monitora_mov=1 aparecem sem limite de data.
        Mesma estrutura de paginação de captura_listar_disponiveis.
        """
        return await _paginar(
            "/v1/api/fila/todos", paginar_tudo, cursor, limite_paginas
        )

    @mcp.tool()
    async def captura_incluir_processo(
        n_processo: str,
        monitora_mov: bool = True,
        baixar_inicial: bool = False,
        data_autuacao: str | None = None,
        classe_processual: str | None = None,
        org_julgador: str | None = None,
        permitir_duplicata: bool = False,
    ) -> Any:
        """Inclui um processo na fila de captura.

        Requer nível de acesso supervisor; erro 403 já tratado em client.py.
        n_processo deve ser o número CNJ; data_autuacao no formato DD/MM/YYYY.
        """
        payload: dict[str, Any] = {
            "n_processo": n_processo,
            "monitora_mov": int(monitora_mov),
            "baixar_inicial": int(baixar_inicial),
            "permitir_duplicata": int(permitir_duplicata),
        }
        if data_autuacao is not None:
            payload["data_autuacao"] = data_autuacao
        if classe_processual is not None:
            payload["classe_processual"] = classe_processual
        if org_julgador is not None:
            payload["org_julgador"] = org_julgador

        return await client.post("/v1/api/fila/processos", payload)
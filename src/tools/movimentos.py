from typing import Any

from fastmcp import FastMCP

from src import client
from src.utils import _com_portal, _paginar


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def captura_listar_com_movimentos(
        paginar_tudo: bool = False,
        cursor: int | None = None,
        limite_paginas: int = 10,
    ) -> dict[str, Any]:
        """Lista processos com movimentações disponíveis para consulta.

        Quando paginar_tudo=False, faz uma única chamada e retorna o cursor para a
        próxima página em proximo_cursor (ha_mais indica se há mais dados).
        Quando paginar_tudo=True, itera o cursor até esgotar ou atingir limite_paginas.
        """
        return await _paginar(
            "/v1/api/movimentos/disponiveis_movimentos",
            paginar_tudo,
            cursor,
            limite_paginas,
        )

    @mcp.tool()
    async def captura_obter_movimentos(id_captura: int) -> dict[str, Any]:
        """Obtém os movimentos de um processo capturado.

        Retorna o response da API diretamente, contendo id_captura, total_linhas e
        movimentos. A estrutura de cada movimento varia por tribunal (campos abertos).
        total_linhas=0 significa sem andamentos visíveis para o usuário autenticado.
        """
        return _com_portal(await client.get(
            "/v1/api/movimentos", params={"id_captura": id_captura}
        ))
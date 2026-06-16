from typing import Any

from fastmcp import FastMCP

from src import client


async def _paginar(
    path: str,
    paginar_tudo: bool,
    cursor: int | None,
    limite_paginas: int,
) -> dict[str, Any]:
    if not paginar_tudo:
        params: dict[str, Any] = {}
        if cursor is not None:
            params["procurar_apos"] = cursor
        resp = await client.get(path, params=params or None)
        proximo = resp.get("procurar_apos")
        return {
            "itens": resp.get("itens", []),
            "total_retornado": resp.get("total_retornado", 0),
            "proximo_cursor": proximo,
            "ha_mais": proximo is not None,
        }

    itens: list[Any] = []
    paginas = 0
    cursor_atual = cursor
    while True:
        params = {}
        if cursor_atual is not None:
            params["procurar_apos"] = cursor_atual
        resp = await client.get(path, params=params or None)
        itens.extend(resp.get("itens", []))
        paginas += 1
        cursor_atual = resp.get("procurar_apos")
        if cursor_atual is None:
            return {
                "itens": itens,
                "total_retornado": len(itens),
                "paginas_consumidas": paginas,
                "interrompido_por_limite": False,
                "proximo_cursor": None,
            }
        if paginas >= limite_paginas:
            return {
                "itens": itens,
                "total_retornado": len(itens),
                "paginas_consumidas": paginas,
                "interrompido_por_limite": True,
                "proximo_cursor": cursor_atual,
            }


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
        return await client.get(
            "/v1/api/movimentos", params={"id_captura": id_captura}
        )

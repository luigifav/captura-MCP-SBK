from typing import Any

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
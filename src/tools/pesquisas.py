from typing import Any

from fastmcp import FastMCP

from src import client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def captura_listar_termos() -> dict[str, Any]:
        """Lista todos os termos de pesquisa ativos monitorados.

        Sem paginação: o endpoint retorna todos os termos de uma vez.
        Retorna {total, itens: [{id, param_pesquisa, status, tipo, tipo_desc,
        data_cadastro}]}. tipo_desc pode ser "NOME" (tipo=0) ou "CPF/CNPJ" (tipo=1).
        """
        return await client.get("/v1/api/pesquisas/termos/ativos")

    @mcp.tool()
    async def captura_criar_termo(
        param_pesquisa: str,
        tipo: int = 0,
    ) -> dict[str, Any]:
        """Cria um novo termo de pesquisa para monitoramento.

        param_pesquisa: nome ou CPF/CNPJ a monitorar.
        tipo: 0=NOME (default), 1=CPF/CNPJ.

        Se já existir um termo inativo com o mesmo valor, a API reativa a linha
        existente em vez de criar duplicata.
        """
        return await client.post(
            "/v1/api/pesquisas/termos",
            {"param_pesquisa": param_pesquisa, "tipo": tipo},
        )

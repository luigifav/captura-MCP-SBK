import base64
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from src import client


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def captura_download_documento(
        id_captura: int,
        retornar_bytes: bool = False,
        salvar_em: str | None = None,
    ) -> dict[str, Any]:
        """Baixa o documento de uma captura via GET /v1/api/download.

        id_captura vem das tools de fila (campo id_captura nos itens retornados
        por captura_listar_disponiveis e captura_listar_todos).

        Por padrão (retornar_bytes=False e salvar_em=None) retorna apenas os
        metadados, omitindo conteudo_base64 para evitar respostas grandes.
        Use salvar_em para gravar o arquivo localmente, ou retornar_bytes=True
        para receber o conteudo_base64 inline.
        """
        resp = await client.get(
            "/v1/api/download", params={"id_captura": id_captura}
        )

        if salvar_em is not None:
            conteudo_base64 = resp.get("conteudo_base64", "")
            dados = base64.b64decode(conteudo_base64)
            destino = Path(salvar_em)
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(dados)
            return {
                "id_captura": resp.get("id_captura"),
                "id_documento": resp.get("id_documento"),
                "tipo_mime": resp.get("tipo_mime"),
                "salvo_em": salvar_em,
                "tamanho_bytes": len(dados),
            }

        if retornar_bytes:
            return {
                **resp,
                "aviso": "conteudo_base64 pode ser grande para PDFs extensos.",
            }

        return {
            "id_captura": resp.get("id_captura"),
            "id_documento": resp.get("id_documento"),
            "tipo_mime": resp.get("tipo_mime"),
            "sucesso": resp.get("sucesso"),
        }

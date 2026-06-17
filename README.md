# captura-MCP-SBK

Servidor MCP (Model Context Protocol) para a API de Captura SBK. Permite consultar processos judiciais, andamentos e documentos em linguagem natural pelo Claude Desktop.

---

## Para clientes: como configurar o Claude Desktop

Abra o arquivo de configuração do Claude Desktop em:

```
C:\Users\<seu-usuario>\AppData\Roaming\Claude\claude_desktop_config.json
```

Adicione a chave `mcpServers` dentro do objeto principal com suas credenciais:

```json
"mcpServers": {
  "captura-mcp-sbk": {
    "url": "https://captura-mcp-sbk.railway.app/mcp",
    "headers": {
      "X-Captura-Login": "seu_login",
      "X-Captura-Senha": "sua_senha"
    }
  }
}
```

Salve o arquivo e reinicie o Claude Desktop. Pronto, sem instalar nada.

---

## Tools disponíveis

| Tool | Descricao |
|---|---|
| `captura_health` | Verifica disponibilidade da API (sem autenticação) |
| `captura_listar_disponiveis` | Lista processos com documento disponível para download (últimos 30 dias) |
| `captura_listar_todos` | Lista todos os processos da fila |
| `captura_incluir_processo` | Inclui um processo na fila (requer permissão de supervisor) |
| `captura_download_documento` | Baixa o documento de uma captura em Base64 |
| `captura_listar_com_movimentos` | Lista processos com movimentações disponíveis |
| `captura_obter_movimentos` | Retorna a linha do tempo de andamentos de um processo |
| `captura_listar_termos` | Lista termos de pesquisa ativos monitorados |
| `captura_criar_termo` | Cadastra um novo termo de monitoramento (nome ou CPF/CNPJ) |

---

## Para desenvolvedores: rodar localmente

### Pré-requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Git

### Instalação

```bash
git clone https://github.com/luigifav/captura-MCP-SBK.git
cd captura-MCP-SBK
uv sync
```

### Configurar credenciais

```bash
cp .env.example .env
```

Edite o `.env`:

```env
CAPTURA_LOGIN=seu_login
CAPTURA_SENHA=sua_senha
CAPTURA_BASE_URL=https://apisbk.sbk.com.br/gtw/api-captura
```

### Configurar o Claude Desktop (modo local)

Descubra o caminho do uv:

```powershell
Get-Command uv | Select-Object -ExpandProperty Source
```

Adicione ao `claude_desktop_config.json`:

```json
"mcpServers": {
  "captura-mcp-sbk": {
    "command": "C:\\Users\\seu.nome\\.local\\bin\\uv.exe",
    "args": [
      "--directory",
      "C:\\Users\\seu.nome\\captura-MCP-SBK",
      "run",
      "captura-mcp"
    ]
  }
}
```

Reinicie o Claude Desktop.

---

## Autenticação

As credenciais são fornecidas por requisição via headers `X-Captura-Login` e `X-Captura-Senha`. O servidor gerencia o token JWT automaticamente por usuário: autentica na primeira chamada, armazena em cache por 55 minutos e reautentica em caso de expiração.

No modo local, as credenciais são lidas do arquivo `.env`.

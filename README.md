# captura-MCP-SBK

Servidor MCP (Model Context Protocol) para a API de Captura SBK. Expõe as ferramentas de captura judicial como tools prontas para uso por agentes de IA, permitindo consultar processos, andamentos e documentos em linguagem natural pelo Claude Desktop.

## Pré-requisitos

- Python 3.12+
- Git
- Claude Desktop

---

## Passo a passo de instalação

### 1. Abrir o PowerShell

Aperte `Win + R`, digite `powershell` e clique em OK.

> Atenção: use o PowerShell, não o CMD. Se rodar os comandos no CMD, vai aparecer o erro `'Set-ExecutionPolicy' nao e reconhecido como um comando interno`.

### 2. Liberar a execução de scripts

```powershell
Set-ExecutionPolicy RemoteSigned -scope CurrentUser
```

Se pedir confirmação, digite `S` e aperte Enter. Se não aparecer nenhuma mensagem, é porque funcionou.

### 3. Instalar o uv

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Ao final aparece a mensagem `everything's installed!`.

> Se aparecer o erro `PowerShell requires an execution policy in [Unrestricted, RemoteSigned, Bypass]`, volte ao passo 2.

### 4. Fechar e reabrir o PowerShell

Feche o PowerShell e abra um novo para o uv ser reconhecido.

### 5. Verificar o caminho do uv

```powershell
Get-Command uv | Select-Object -ExpandProperty Source
```

Anote o caminho que aparecer. Exemplo: `C:\Users\luigi.faveri\.local\bin\uv.exe`. Ele vai ser usado na configuração do Claude Desktop.

> Se rodar `where uv` e não retornar nada, use o comando acima no lugar.

### 6. Clonar o repositório

```powershell
git clone https://github.com/luigifav/captura-MCP-SBK.git
cd captura-MCP-SBK
```

> Se estiver usando o Git Bash e o `cd captura-MCP-SBK` der erro, rode `ls` primeiro para ver o nome exato da pasta criada.

### 7. Instalar as dependências

```powershell
uv sync
```

### 8. Configurar as credenciais

```powershell
cp .env.example .env
```

Abra o arquivo `.env` e preencha com seu login e senha da API de Captura:

```env
CAPTURA_LOGIN=seu_login
CAPTURA_SENHA=sua_senha
CAPTURA_BASE_URL=https://apisbk.sbk.com.br/gtw/api-captura
```

### 9. Configurar o Claude Desktop

Abra o arquivo de configuração do Claude Desktop em:

```
C:\Users\<seu-usuario>\AppData\Roaming\Claude\claude_desktop_config.json
```

Adicione a chave `mcpServers` dentro do objeto principal, substituindo os caminhos pelos seus:

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

- `command`: caminho do uv obtido no passo 5
- `--directory`: caminho da pasta onde o repositório foi clonado

### 10. Reiniciar o Claude Desktop

Feche e abra o Claude Desktop. O servidor MCP será carregado automaticamente.

### 11. Testar

No Claude Desktop, pergunte:

> "Qual processo eu tenho?"

Se tudo estiver certo, o Claude vai buscar os dados da API e responder com os processos disponíveis.

---

## Tools disponíveis

| Tool | Descricao |
|------|-----------|
| `captura_health` | Verifica disponibilidade da API (sem autenticação) |
| `captura_listar_disponiveis` | Lista processos com documento disponível para download (últimos 30 dias) |
| `captura_listar_todos` | Lista todos os processos da fila |
| `captura_incluir_processo` | Inclui um processo na fila (requer permissão de supervisor) |
| `captura_download_documento` | Baixa o documento de uma captura em Base64 |
| `captura_listar_com_movimentos` | Lista processos com movimentações disponíveis |
| `captura_obter_movimentos` | Retorna a linha do tempo de andamentos de um processo |
| `captura_listar_termos` | Lista termos de pesquisa ativos monitorados |
| `captura_criar_termo` | Cadastra um novo termo de monitoramento (nome ou CPF/CNPJ) |

## Autenticação

O servidor gerencia o token JWT automaticamente: autentica na primeira chamada, armazena em cache por 55 minutos e reautentica em caso de expiração (401).

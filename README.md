# TuxAssist — MCP AI Agent (Python / Termux)

TuxAssist é um agente de inteligência artificial avançado integrado ao **MCP (Model Context Protocol)** para listar arquivos, ler códigos, executar comandos no terminal de forma segura e interagir com dispositivos IoT (como ESP32-S3), executável diretamente no Termux ou Linux via Python.

## Arquitetura do Projeto

- `chat.py` — Interface principal do agente de IA (CLI interativa com suporte a múltiplos provedores).
- `servidor_mcp.py` — Servidor MCP e ferramentas (listar arquivos, ler arquivo, executar comandos, ESP32).
- `security.py` — Validação de Path Traversal e classificação de risco de comandos.
- `config.py` — Gerenciamento e persistência do diretório de trabalho (`tuxassist_config.json`).
- `requirements.txt` — Dependências Python.
- `test_tuxassist.py` — Testes automatizados unitários.

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

Inicie o assistente com:

```bash
python chat.py
```

## Comandos Úteis no Chat

- `/home <caminho>` — Altera e persiste o diretório de trabalho padrão (utilizado pelas ferramentas MCP).
- `/provider <gemini|groq|openai>` — Altera o provedor de IA.
- `/model <nome_modelo>` — Altera o modelo utilizado.
- `/help` — Exibe ajuda.
- `sair` — Encerra o assistente.
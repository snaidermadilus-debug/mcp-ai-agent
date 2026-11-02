​📦 2. Dependências do Projeto Puro (Só Termux local)
​Se o usuário não tem um ESP32 e quer usar o TuxAssist apenas como um agente
de Inteligência Artificial para ler arquivos, programar e rodar
 scripts direto no terminal do celular/PC, o setup é muito mais rápido.

​🐍 Ambiente Python (Termux / Linux / Windows)
​Como ele não vai compilar nada de hardware, a única dependência é o ambiente Python.
 O comando é exatamente o mesmo:
​
  Comando de instalação:

python -m pip install google-genai rich mcp




(`'python -m pip install google-genai rich mcp``)


Bibliotecas Nativas Utilizadas (Não precisam ser instaladas, já vêm no Python):
​os (Navegação de arquivos e limpeza de tela)
​json (Processamento dos dados da IA)
​asyncio (Rotinas assíncronas do MCP)
​urllib.request (Comunicação HTTP ultra-leve com Groq e OpenAI)
​subprocess (O motor que dá vida à ferramenta de rodar comandos no shell)




 git clone https://github.com/snaidermadilus-debug/mcp-ai-agent.git
 cd mcp-ai-agent











<a href="https://github.com/snaidermadilus-debug/mcp-ai-agent/archive/refs/heads/main.zip"
   download>
    📦 Baixar MCP Server
</a>








Crie conta em https://console.groq.com/keys

Crie API Key
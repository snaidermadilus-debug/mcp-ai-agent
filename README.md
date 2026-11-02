🤖 TuxAssist — Agente de IA com MCP para Termux/Linux/Windows

«Um agente de Inteligência Artificial que pode conversar com você, ler seus arquivos, analisar códigos e executar comandos no terminal através de ferramentas MCP.»

O TuxAssist é um agente de IA executado diretamente no terminal.

Ele conecta um modelo de Inteligência Artificial a um servidor MCP local, permitindo que a IA utilize ferramentas do seu próprio ambiente.

🚀 O que ele consegue fazer?

- 📂 Listar arquivos e diretórios
- 📄 Ler arquivos e códigos
- 💻 Executar comandos no terminal
- 🧠 Usar diferentes provedores de IA
- 🔌 Utilizar ferramentas MCP
- ⚡ Trabalhar diretamente no Termux
- 🛠️ Ajudar a programar e executar scripts
- 🤖 Conversar com Gemini, Groq ou OpenAI
- 📡 Possibilidade de integração com ESP32 através do servidor MCP

---

🧠 Como o TuxAssist funciona?

A arquitetura é simples:

                    ┌──────────────────────┐
                    │       USUÁRIO        │
                    │      Terminal        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       chat.py        │
                    │   Interface + IA     │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │                      │
                    ▼                      ▼
             ┌─────────────┐       ┌─────────────┐
             │   Gemini    │       │ Groq/OpenAI │
             │   Google    │       │     API     │
             └─────────────┘       └─────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   servidor_mcp.py    │
                    │      MCP Server      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        📂 Arquivos       💻 Terminal       🔌 ESP32

O "chat.py" é o cliente.

Ele conversa com o modelo de IA e também inicia o "servidor_mcp.py" como um processo MCP local. O servidor disponibiliza as ferramentas que a IA pode chamar.

---

🧰 Ferramentas MCP

O "servidor_mcp.py" disponibiliza ferramentas para o agente.

📂 "listar_arquivos"

Lista arquivos de uma pasta e percorre suas subpastas.

listar_arquivos(".")

Também ignora diretórios ocultos e "__pycache__", limitando a saída para evitar respostas gigantes.

📄 "ler_arquivo"

Lê o conteúdo de um arquivo de texto.

ler_arquivo("script.py")

Isso permite que a IA analise diretamente seus códigos e arquivos.

💻 "executar_comando"

Executa comandos no terminal.

executar_comando("python script.py")

O servidor utiliza "subprocess" para executar o comando e devolver a saída para a IA.

🔌 "comando_remoto_esp32"

O projeto também possui uma ferramenta destinada à comunicação com um ESP32 através da rede local.

---

📱 1. Instalação no Termux

Atualizar o Termux

pkg update -y && pkg upgrade -y

Instalar Python e Git

pkg install python git -y

Conferir instalação

python --version
git --version

---

📥 2. Baixar o projeto

Clone o repositório:

git clone https://github.com/snaidermadilus-debug/mcp-ai-agent.git

Entre na pasta:

cd mcp-ai-agent

Ou faça tudo de uma vez:

git clone https://github.com/snaidermadilus-debug/mcp-ai-agent.git && cd mcp-ai-agent

---

📦 3. Dependências

O TuxAssist utiliza Python e algumas bibliotecas externas.

Instalação completa

python -m pip install -U google-genai rich mcp prompt_toolkit

O que cada biblioteca faz?

Biblioteca| Função
"google-genai"| Comunicação com a API Gemini
"rich"| Interface visual do terminal
"mcp"| Cliente/servidor Model Context Protocol
"prompt_toolkit"| Interface avançada de entrada no terminal

O "chat.py" importa diretamente "mcp", "rich", "google-genai" e "prompt_toolkit".

Bibliotecas nativas do Python

Estas não precisam ser instaladas separadamente:

os
json
asyncio
urllib.request
urllib.error
subprocess
shutil
socket

Elas são usadas para operações de arquivos, configuração, comunicação HTTP, execução de processos e operações do sistema.

---

🔑 4. Configurar uma Inteligência Artificial

O TuxAssist permite escolher entre:

1) Gemini (Google)
2) Groq
3) OpenAI

Essa seleção já existe no "chat.py".

---

🟢 Gemini — Google

Se você já possui uma conta Google, não precisa criar outra.

Criar sua API Key do Gemini

👉 "Google AI Studio" (https://aistudio.google.com/)

👉 "Documentação oficial da Gemini API" (https://ai.google.dev/gemini-api/docs/get-started)

No Google AI Studio:

1. Entre com sua conta Google
2. Abra a área de API Keys
3. Crie uma API Key
4. Copie a chave
5. Cole no TuxAssist quando ele solicitar

O Google AI Studio fornece o projeto e a chave para novos usuários, e a documentação oficial recomenda manter a chave protegida.

No TuxAssist

Execute:

python chat.py

Escolha:

1) Gemini (Google)

Depois cole sua API Key.

---

⚡ Groq

O Groq é uma alternativa focada em inferência rápida.

Criar conta / acessar API Keys

👉 "Groq Console — API Keys" (https://console.groq.com/keys)

Depois:

1. Entre ou crie sua conta
2. Abra API Keys
3. Crie uma nova API Key
4. Copie a chave
5. Cole no TuxAssist

A documentação oficial do Groq também recomenda configurar a chave como variável de ambiente e mantê-la secreta.

---

🟠 OpenAI

O TuxAssist também possui suporte para OpenAI.

👉 "Plataforma OpenAI" (https://platform.openai.com/)

Crie sua API Key e informe ao TuxAssist quando ele solicitar.

---

▶️ 5. Executar o TuxAssist

Dentro da pasta do projeto:

cd ~/mcp-ai-agent

Execute:

python chat.py

O TuxAssist iniciará:

TuxAssist
   ↓
Escolha da IA
   ↓
API
   ↓
Servidor MCP
   ↓
Ferramentas

O próprio "chat.py" inicia o servidor MCP através de:

StdioServerParameters(
    command="python",
    args=["servidor_mcp.py"]
)

Depois ele inicializa a sessão MCP e descobre as ferramentas disponíveis.

---

🖥️ 6. Comandos do TuxAssist

Durante a utilização, alguns comandos especiais estão disponíveis:

/mu

Trocar o provedor/modelo de IA.

/clear

Limpar a tela.

/ls

Listar arquivos.

!cmd

Executar comando no terminal.

/sair

Encerrar o TuxAssist.

Esses comandos também aparecem diretamente na interface do programa.

---

💻 7. Exemplos de utilização

Depois de iniciar:

python chat.py

Você pode pedir:

Liste os arquivos desta pasta.

O agente poderá utilizar:

listar_arquivos

---

Você pode pedir:

Leia o arquivo servidor_mcp.py e explique o código.

O agente poderá utilizar:

ler_arquivo

---

Você pode pedir:

Execute python --version

O agente poderá utilizar:

executar_comando

---

Você também pode pedir:

Analise meu projeto e diga quais arquivos são importantes.

O TuxAssist pode combinar várias ferramentas MCP para realizar a tarefa.

---

📁 8. Estrutura do projeto

mcp-ai-agent/
│
├── chat.py
│   └── Cliente principal
│       ├── Interface do terminal
│       ├── Configuração da IA
│       ├── Gemini
│       ├── Groq
│       ├── OpenAI
│       └── Cliente MCP
│
├── servidor_mcp.py
│   └── Servidor MCP
│       ├── listar_arquivos
│       ├── ler_arquivo
│       ├── executar_comando
│       └── comando_remoto_esp32
│
├── tuxassist_config.json
│   └── Criado localmente para guardar
│       as configurações escolhidas
│
└── README.md
    └── Documentação

«⚠️ Nunca publique sua API Key no GitHub.»

O arquivo de configuração local pode conter credenciais dependendo de como o projeto foi configurado. As chaves devem ser tratadas como senhas e não devem ser commitadas no repositório. A própria documentação do Gemini recomenda não colocar API Keys no código-fonte ou controle de versão.

---

🧠 9. O que é MCP?

MCP = Model Context Protocol.

É um protocolo que permite conectar modelos de Inteligência Artificial a ferramentas externas.

Neste projeto:

IA
 │
 ▼
MCP Client
 │
 ▼
MCP Server
 │
 ├── 📂 Arquivos
 ├── 📄 Leitura
 ├── 💻 Terminal
 └── 🔌 ESP32

Isso significa que a IA não fica limitada apenas a responder texto.

Ela pode usar ferramentas para interagir com o ambiente local.

---

🛠️ 10. Tecnologias utilizadas

- 🐍 Python
- 🤖 Google Gemini API
- ⚡ Groq API
- 🧠 OpenAI API
- 🔌 Model Context Protocol (MCP)
- 🎨 Rich
- ⌨️ Prompt Toolkit
- 📱 Termux
- 🐧 Linux
- 💻 Windows
- 🔌 ESP32

---

🚀 11. Instalação rápida — copiar e colar

Para Termux:

pkg update -y && pkg upgrade -y && pkg install python git -y && git clone https://github.com/snaidermadilus-debug/mcp-ai-agent.git && cd mcp-ai-agent && python -m pip install -U google-genai rich mcp prompt_toolkit && python chat.py

Depois escolha seu provedor:

1 → Gemini
2 → Groq
3 → OpenAI

Cole sua API Key e comece a usar.

---

🔗 Links importantes

📦 Projeto

👉 https://github.com/snaidermadilus-debug/mcp-ai-agent

🟢 Google

👉 https://accounts.google.com/signup

🧠 Google AI Studio / Gemini

👉 https://aistudio.google.com/

📚 Gemini API

👉 https://ai.google.dev/gemini-api/docs/get-started

⚡ Groq API Keys

👉 https://console.groq.com/keys

🟠 OpenAI

👉 https://platform.openai.com/

---

⚠️ Aviso de segurança

O TuxAssist possui uma ferramenta capaz de executar comandos através do shell.

Isso significa que os comandos solicitados pelo agente podem ter efeitos reais no sistema.

Não execute comandos fornecidos por fontes desconhecidas sem entender o que eles fazem.

Além disso:

❌ Não publique API Keys
❌ Não coloque tokens no Git
❌ Não compartilhe tuxassist_config.json se ele contiver credenciais
❌ Não execute comandos desconhecidos sem verificar

---

⭐ Projeto

Se este projeto foi útil para você, considere dar uma ⭐ no GitHub.

TuxAssist — IA + MCP + Terminal + Automação

🤖 IA
 +
🔌 MCP
 +
💻 Terminal
 +
📂 Arquivos
 +
⚡ Automação
 =
🚀 TuxAssist
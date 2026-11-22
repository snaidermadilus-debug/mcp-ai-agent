import os
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
import re

from config import load_config, save_config, get_active_workspace, set_active_workspace
from servidor_mcp import ServidorMCP

# Simple dotenv loader
def load_env_file():
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except Exception:
            pass

load_env_file()

# Tenta importar Google GenAI SDK moderno
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

class TuxAssistCLI:
    def __init__(self):
        self.config = load_config()
        self.provider = self.config.get("provider", "gemini")
        self.model = self.config.get("model", "gemini-2.5-flash")
        self.api_key = self.config.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        self.mcp = ServidorMCP()
        self.history = []

    def print_banner(self):
        print("\033[1;36m" + "="*60)
        print(" 🤖 TUXASSIST WEB — MCP AI AGENT (Python / Termux)")
        print("="*60 + "\033[0m")
        print(f" Workspace Ativo: {get_active_workspace()}")
        print(f" Provedor: {self.provider} | Modelo: {self.model}")
        print(" Digite '/home <caminho>' para alterar o diretório de trabalho.")
        print(" Digite '/help' para ver os comandos ou 'sair' para encerrar.")
        print("-" * 60 + "\033[0m")

    def handle_command(self, user_input: str) -> bool:
        cmd = user_input.strip()
        if cmd.lower() in ("sair", "exit", "quit"):
            print("\n👋 Até logo! TuxAssist encerrado.")
            return False
        
        if cmd.startswith("/home"):
            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                print(f"\n📂 Workspace atual: {get_active_workspace()}")
                print("Uso: /home <caminho_do_diretorio>")
            else:
                success, msg = set_active_workspace(parts[1])
                print(f"\n{msg}")
            return True

        if cmd.startswith("/provider"):
            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                print(f"Provedor atual: {self.provider}. Opções: gemini, groq, openai")
            else:
                p = parts[1].strip().lower()
                if p in ("gemini", "groq", "openai"):
                    self.provider = p
                    save_config({"provider": p})
                    print(f"Provedor alterado para: {p}")
                else:
                    print("Provedor inválido. Escolha: gemini, groq, openai")
            return True

        if cmd.startswith("/model"):
            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                print(f"Modelo atual: {self.model}")
            else:
                m = parts[1].strip()
                self.model = m
                save_config({"model": m})
                print(f"Modelo alterado para: {m}")
            return True

        if cmd == "/help":
            print("\nComandos disponíveis:")
            print("  /home <caminho>  - Altera e persiste o diretório de trabalho")
            print("  /provider <nome> - Altera o provedor LLM (gemini, groq, openai)")
            print("  /model <modelo>  - Altera o modelo de IA")
            print("  /help            - Exibe esta ajuda")
            print("  sair / exit      - Encerra o assistente\n")
            return True

        return None

    def call_llm(self, messages: list) -> tuple[str, list]:
        system_instruction = "Você é o TuxAssist, um assistente inteligente com acesso a ferramentas MCP para listar arquivos, ler códigos e executar comandos no terminal. Responda de forma prestativa, técnica e direta em português."
        execution_steps = []

        if self.provider == "gemini":
            if not HAS_GENAI_SDK:
                return "Erro: O pacote google-genai não está instalado no ambiente Python.", []
            
            client = genai.Client(api_key=self.api_key or os.getenv("GEMINI_API_KEY"))
            
            contents = []
            for m in messages:
                role = "model" if m["role"] == "assistant" else "user"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

            tools_def = [types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=td["name"],
                    description=td["description"],
                    parameters=td["parameters"]
                ) for td in self.mcp.get_tool_definitions()
            ])]

            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_def,
                temperature=0.7
            )

            try:
                response = client.models.generate_content(
                    model=self.model or "gemini-2.5-flash",
                    contents=contents,
                    config=config
                )
            except Exception as e:
                return f"Erro na API Gemini: {e}", []

            while response.function_calls:
                for fc in response.function_calls:
                    fn_name = fc.name
                    fn_args = fc.args or {}
                    
                    print(f"\n\033[1;33m⚙️ Executando ferramenta MCP: {fn_name}({fn_args})\033[0m")
                    tool_res = self.mcp.executar_ferramenta(fn_name, fn_args)
                    
                    execution_steps.append({
                        "tool": fn_name,
                        "args": fn_args,
                        "result": tool_res
                    })

                    contents.append(response.candidates[0].content)
                    contents.append(types.Content(role="user", parts=[
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_res[:4000]}
                        )
                    ]))

                try:
                    response = client.models.generate_content(
                        model=self.model or "gemini-2.5-flash",
                        contents=contents,
                        config=config
                    )
                except Exception as e:
                    return f"Erro na API Gemini (tool call loop): {e}", execution_steps

            return response.text or "Sem resposta do modelo.", execution_steps

        else:
            url = "https://api.groq.com/openai/v1/chat/completions" if self.provider == "groq" else "https://api.openai.com/v1/chat/completions"
            key = self.api_key or os.getenv("GROQ_API_KEY" if self.provider == "groq" else "OPENAI_API_KEY")

            openai_tools = [{
                "type": "function",
                "function": {
                    "name": td["name"],
                    "description": td["description"],
                    "parameters": td["parameters"]
                }
            } for td in self.mcp.get_tool_definitions()]

            formatted_messages = [{"role": "system", "content": system_instruction}] + [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]

            payload = {
                "model": self.model or ("llama-3.3-70b-versatile" if self.provider == "groq" else "gpt-4o"),
                "messages": formatted_messages,
                "tools": openai_tools,
                "tool_choice": "auto"
            }

            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }, method="POST")

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                return f"Erro na API {self.provider} ({e.code}): {err_body}", []
            except Exception as e:
                return f"Erro de conexão com {self.provider}: {e}", []

            msg = data["choices"][0]["message"]

            while msg.get("tool_calls"):
                formatted_messages.append(msg)
                for tc in msg["tool_calls"]:
                    f_name = tc["function"]["name"]
                    f_args = json.loads(tc["function"]["arguments"] or "{}")
                    
                    print(f"\n\033[1;33m⚙️ Executando ferramenta MCP: {f_name}({f_args})\033[0m")
                    tool_res = self.mcp.executar_ferramenta(f_name, f_args)

                    execution_steps.append({
                        "tool": f_name,
                        "args": f_args,
                        "result": tool_res
                    })

                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": f_name,
                        "content": tool_res[:4000]
                    })

                payload["messages"] = formatted_messages
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json"
                }, method="POST")

                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                    msg = data["choices"][0]["message"]
                except Exception:
                    break

            return msg.get("content") or "Sem resposta.", execution_steps

    def run(self):
        self.print_banner()
        while True:
            try:
                user_input = input("\n\033[1;32mTuxAssist>\033[0m ")
                if not user_input.strip():
                    continue
                
                cmd_handled = self.handle_command(user_input)
                if cmd_handled is False:
                    break
                if cmd_handled is True:
                    continue

                self.history.append({"role": "user", "content": user_input})
                print("\n\033[1;35m🤖 Pensando...\033[0m")

                reply, steps = self.call_llm(self.history)

                requires_conf = None
                for step in steps:
                    res_text = step.get("result", "")
                    if "[CONFIRMATION_REQUIRED" in res_text:
                        match = re.search(r'\[CONFIRMATION_REQUIRED:(\d+):(.*?):(.*?)]', res_text)
                        if match:
                            risk = match.group(1)
                            cmd = urllib.parse.unquote(match.group(2))
                            reason = urllib.parse.unquote(match.group(3))
                            requires_conf = (cmd, risk, reason)
                            break

                if requires_conf:
                    cmd_to_confirm, risk_level, reason = requires_conf
                    print(f"\n\033[1;31m⚠️ ALERTA DE SEGURANÇA (Nível {risk_level})\033[0m")
                    print(f"Motivo: {reason}")
                    print(f"Comando: \033[1m{cmd_to_confirm}\033[0m")
                    choice = input("Deseja autorizar a execução deste comando? [s/N]: ").strip().lower()
                    
                    if choice in ("s", "sim", "y", "yes"):
                        print("\n\033[1;33m🔄 Executando comando confirmado...\033[0m")
                        conf_res = self.mcp.executar_comando(cmd_to_confirm, confirmed=True)
                        print(f"\n\033[1;36mResultado:\033[0m\n{conf_res}")
                        reply += f"\n\n*Comando executado após confirmação do usuário:*\n```\n{conf_res}\n```"
                    else:
                        print("\n❌ Operação cancelada pelo usuário.")
                        reply += f"\n\n*Operação cancelada pelo usuário para o comando:* `{cmd_to_confirm}`"

                print(f"\n\033[1;34m🤖 TuxAssist:\033[0m\n{reply}")
                self.history.append({"role": "assistant", "content": reply})

            except KeyboardInterrupt:
                print("\n\n👋 Encerrado pelo usuário.")
                break
            except Exception as e:
                print(f"\n\033[1;31m❌ Erro: {e}\033[0m")

if __name__ == "__main__":
    cli = TuxAssistCLI()
    cli.run()

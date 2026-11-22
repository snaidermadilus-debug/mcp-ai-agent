import os
import sys
import json
import shutil
import asyncio
import time
import random
import email.utils
import datetime
import urllib.request
import urllib.error
import socket

try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
    MCP_CLIENT_DISPONIVEL = True
except ImportError:
    MCP_CLIENT_DISPONIVEL = False

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    from rich.text import Text
    from rich import box
    RICH_DISPONIVEL = True
except ImportError:
    RICH_DISPONIVEL = False
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
        def status(self, *args, **kwargs):
            class DummyStatus:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def update(self, *args): pass
            return DummyStatus()
    class Markdown:
        def __init__(self, t): self.t = t
    class Panel:
        @staticmethod
        def fit(t, **kw): return t
    class Prompt:
        @staticmethod
        def ask(t, **kw): return input(t + " ")
    class Table:
        @staticmethod
        def grid(*args, **kw):
            class DG:
                def add_column(self, *a, **k): pass
                def add_row(self, *a, **k): pass
            return DG()
    class Text:
        def __init__(self, t="", **kw): self.t = t
        def append(self, *a, **k): pass
    box = type('Box', (), {'ROUNDED': 1})()

from config import carregar_config, salvar_config, mascarar_chave, MAX_HISTORY_MESSAGES, LIMITE_TOKENS_FERRAMENTA
from security import validate_command

# Independent provider loading (graceful degradation if google-genai is missing)
GEMINI_DISPONIVEL = False
try:
    from google import genai
    from google.genai import types
    GEMINI_DISPONIVEL = True
except ImportError:
    pass

try:
    from prompt_toolkit import Application
    from prompt_toolkit.widgets import TextArea, Frame
    from prompt_toolkit.widgets.base import Border
    from prompt_toolkit.layout import Layout, HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.layout.dimension import Dimension
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
    Border.TOP_LEFT = "╭"
    Border.TOP_RIGHT = "╮"
    Border.BOTTOM_LEFT = "╰"
    Border.BOTTOM_RIGHT = "╯"
    TEM_PT = True
    HISTORICO = InMemoryHistory()
except ImportError:
    TEM_PT = False

console = Console()

LARANJA = "#d97757"
CINZA = "grey50"

def limitar_texto(texto, limite=LIMITE_TOKENS_FERRAMENTA):
    """Corta a saída antes de mandar pra API, limitando o consumo de caracteres/tokens."""
    texto = texto or ""
    if len(texto) <= limite:
        return texto
    cortado = len(texto) - limite
    return texto[:limite] + f"\n\n[...saída cortada, {cortado} caracteres omitidos...]"

def compactar_historico(messages, max_msgs=MAX_HISTORY_MESSAGES):
    """Compacta o histórico preservando a integridade de tool_calls e tool responses."""
    if len(messages) <= max_msgs:
        return messages
    
    system_msg = messages[0] if messages and messages[0].get('role') == 'system' else None
    start_idx = 1 if system_msg else 0
    
    recent_msgs = messages[start_idx:]
    
    while len(recent_msgs) > (max_msgs - (1 if system_msg else 0)):
        removed = recent_msgs.pop(0)
        if removed.get('tool_calls'):
            while recent_msgs and recent_msgs[0].get('role') == 'tool':
                recent_msgs.pop(0)

    return ([system_msg] if system_msg else []) + recent_msgs

def banner(provedor=None, modelo=None):
    linhas = f"Bem-vindo ao TuxAssist\n\n/mu trocar IA · /clear limpar · /ls listar · !cmd rodar · /sair"
    if provedor and modelo:
        linhas += f"\n\nmodelo: {provedor.upper()} · {modelo}\ncwd: {os.getcwd()}"
    console.print(linhas)

def titulo(texto):
    console.print(f"\n● {texto}")

def opcao(n, texto):
    console.print(f"  {n}) {texto}")

def setup_ia(config, mudar_agora=False):
    os.system("cls" if os.name == "nt" else "clear")
    banner()

    p_salvo = config.get("provedor_atual")
    m_salvo = config.get("modelo_atual")

    if not mudar_agora and p_salvo and m_salvo and config.get(f"{p_salvo}_key"):
        console.print(f"Sessão anterior encontrada: {p_salvo.upper()} - {m_salvo}")
        resp = Prompt.ask("Reconectar com essa configuração? (S/n)", default="s").strip().lower()
        if resp == "s":
            return p_salvo, config[f"{p_salvo}_key"], m_salvo

    titulo("Escolha o motor de Inteligência Artificial")
    if GEMINI_DISPONIVEL:
        opcao(1, "Gemini (Google)")
    else:
        console.print("  1) Gemini (Google) — Indisponível (falta google-genai)")
    opcao(2, "Groq (Llama, Mixtral - Ultra rápido)")
    opcao(3, "OpenAI (ChatGPT)")

    provedor = ""
    while True:
        op = Prompt.ask("Opção (1 a 3)")
        if op == '1':
            if not GEMINI_DISPONIVEL:
                console.print("Erro: Biblioteca 'google-genai' não instalada. Escolha Groq ou OpenAI.")
                continue
            provedor = "gemini"; break
        if op == '2': provedor = "groq"; break
        if op == '3': provedor = "openai"; break

    chave_salva = config.get(f"{provedor}_key", "")
    if chave_salva:
        k = Prompt.ask(f"Chave {provedor.capitalize()} salva ({mascarar_chave(chave_salva)})! ENTER para usar a mesma ou cole uma nova", default="", show_default=False)
        api_key = k.strip() if k.strip() else chave_salva
    else:
        api_key = Prompt.ask(f"Cole sua API Key da {provedor.capitalize()}").strip()

    titulo(f"Escolha o modelo da {provedor.capitalize()}")
    modelo = ""

    if provedor == "gemini":
        opcao(1, "gemini-2.5-flash (Recomendado)")
        opcao(2, "gemini-2.5-pro")
        opcao(3, "Digitar outro nome")
        op = Prompt.ask("Opção")
        if op == '1': modelo = "gemini-2.5-flash"
        elif op == '2': modelo = "gemini-2.5-pro"
        else: modelo = Prompt.ask("Nome do modelo").strip()

    elif provedor == "groq":
        opcao(1, "llama-3.3-70b-versatile (Recomendado)")
        opcao(2, "mixtral-8x7b-32768")
        opcao(3, "Digitar outro nome")
        op = Prompt.ask("Opção")
        if op == '1': modelo = "llama-3.3-70b-versatile"
        elif op == '2': modelo = "mixtral-8x7b-32768"
        else: modelo = Prompt.ask("Nome do modelo").strip()

    elif provedor == "openai":
        opcao(1, "gpt-4o (Recomendado)")
        opcao(2, "gpt-4o-mini")
        opcao(3, "Digitar outro nome")
        op = Prompt.ask("Opção")
        if op == '1': modelo = "gpt-4o"
        elif op == '2': modelo = "gpt-4o-mini"
        else: modelo = Prompt.ask("Nome do modelo").strip()

    config[f"{provedor}_key"] = api_key
    config["provedor_atual"] = provedor
    config["modelo_atual"] = modelo
    salvar_config(config)

    return provedor, api_key, modelo

async def chamar_api_com_retry(url, headers, payload, max_retries=3, timeout=30):
    """Executa requisição HTTP assíncrona com timeout, tratamento de erros 400/401/403/404/429/5xx, backoff exponencial, jitter e Retry-After."""
    tentativa = 0
    while tentativa < max_retries:
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            
            def _do_request():
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    data = response.read(10 * 1024 * 1024)
                    return json.loads(data.decode('utf-8'))

            return await asyncio.to_thread(_do_request)

        except urllib.error.HTTPError as he:
            code = he.code
            err_body = he.read().decode('utf-8', errors='replace')
            
            if code == 400:
                raise RuntimeError(f"Erro HTTP 400 (Bad Request): {err_body}")
            if code == 401:
                raise RuntimeError(f"Erro HTTP 401 (Unauthorized - API Key inválida ou expirada): {err_body}")
            if code == 403:
                raise RuntimeError(f"Erro HTTP 403 (Forbidden): {err_body}")
            if code == 404:
                raise RuntimeError(f"Erro HTTP 404 (Not Found): {err_body}")
            
            if code in [429, 500, 502, 503, 504]:
                tentativa += 1
                if tentativa >= max_retries:
                    raise RuntimeError(f"Erro HTTP {code} após {max_retries} tentativas: {err_body}")
                
                retry_after_header = he.headers.get("Retry-After")
                sleep_time = None
                if retry_after_header:
                    if retry_after_header.isdigit():
                        sleep_time = float(retry_after_header)
                    else:
                        try:
                            dt = email.utils.parsedate_to_datetime(retry_after_header)
                            if dt:
                                delta = (dt - datetime.datetime.now(datetime.timezone.utc)).total_seconds()
                                sleep_time = max(0.0, delta)
                        except Exception:
                            pass
                
                if sleep_time is None:
                    sleep_time = (2 ** tentativa) + random.uniform(0, 1)
                
                await asyncio.sleep(sleep_time)
                continue
            else:
                raise RuntimeError(f"Erro HTTP ({code}): {err_body}")

        except (urllib.error.URLError, socket.gaierror, TimeoutError, ConnectionResetError) as ue:
            tentativa += 1
            if tentativa >= max_retries:
                raise RuntimeError(f"Falha de conexão ou timeout após {max_retries} tentativas: {ue}")
            await asyncio.sleep((2 ** tentativa) + random.uniform(0, 1))
    
    raise RuntimeError("Falha na comunicação com a API após tentativas máximas.")

async def pedir_entrada():
    if not TEM_PT:
        largura = shutil.get_terminal_size((80, 20)).columns
        print("-" * largura)
        try:
            texto = input("> ")
        except (KeyboardInterrupt, EOFError):
            raise
        return texto

    campo = TextArea(
        prompt=[("fg:#d97757 bold", "> ")],
        multiline=True,
        wrap_lines=True,
        history=HISTORICO,
        height=Dimension(min=1, max=5),
    )

    kb = KeyBindings()

    @kb.add("enter", eager=True)
    def _enviar(event):
        event.app.exit(result=campo.text)

    @kb.add("escape", "enter")
    def _nova_linha(event):
        campo.buffer.insert_text("\n")

    @kb.add("c-c")
    def _cancelar(event):
        event.app.exit(exception=KeyboardInterrupt())

    @kb.add("c-d")
    def _sair(event):
        if not campo.text:
            event.app.exit(exception=EOFError())

    dica = Window(
        FormattedTextControl([("fg:#808080", "  /mu trocar IA · /clear limpar · /ls listar · !cmd rodar · alt+enter nova linha")]),
        height=1,
    )

    layout = Layout(HSplit([Frame(campo), dica]), focused_element=campo)
    estilo = Style.from_dict({"frame.border": "#808080"})

    app = Application(layout=layout, key_bindings=kb, style=estilo, full_screen=False)
    return await app.run_async() or ""

def mostrar_ferramenta(nome, args):
    try:
        if isinstance(args, str):
            args = json.loads(args)
        partes = ", ".join(f"{k}={repr(v)[:60]}" for k, v in dict(args).items())
    except Exception:
        partes = str(args)[:80]
    console.print(f"● {nome}({partes})")

def mostrar_resultado(texto, max_linhas=4):
    linhas = (texto or "").strip().splitlines() or ["(sem saída)"]
    for i, l in enumerate(linhas[:max_linhas]):
        prefixo = "  ⎿  " if i == 0 else "     "
        console.print(f"{prefixo}{l[:150]}")
    if len(linhas) > max_linhas:
        console.print(f"     … +{len(linhas) - max_linhas} linhas")

def mostrar_resposta(texto):
    console.print(f"● {texto}\n")

async def main():
    if not MCP_CLIENT_DISPONIVEL:
        console.print("Erro: Biblioteca 'mcp' não instalada.")
        return

    config = carregar_config()
    provedor, api_key, modelo = setup_ia(config)

    os.system("cls" if os.name == "nt" else "clear")
    banner(provedor, modelo)
    console.print("Conectando ao servidor MCP...")

    mcp_script_path = os.path.abspath("servidor_mcp.py")
    server_params = StdioServerParameters(command=sys.executable, args=[mcp_script_path])

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = await session.list_tools()
                valid_tool_names = {t.name for t in mcp_tools.tools}

                gemini_tools = [{"function_declarations": [
                    {"name": t.name, "description": t.description, "parameters": t.input_schema}
                    for t in mcp_tools.tools
                ]}] if GEMINI_DISPONIVEL else []

                openai_tools = [{"type": "function", "function": {
                    "name": t.name, "description": t.description, "parameters": t.input_schema
                }} for t in mcp_tools.tools]

                instrucoes = (
                    "Você é o TuxAssist, um assistente com acesso a ferramentas MCP para listar arquivos, ler códigos e executar comandos no terminal.\n"
                    "REGRAS:\n"
                    "- Para listar pastas, use 'listar_arquivos'.\n"
                    "- Para ler arquivos, use 'ler_arquivo'.\n"
                    "- Para comandos no sistema, use 'executar_comando'."
                )

                cliente_gemini = None

                def inicializar_ia(p, k, m):
                    nonlocal cliente_gemini
                    if p == "gemini":
                        if not GEMINI_DISPONIVEL:
                            raise RuntimeError("Google GenAI indisponível.")
                        cliente_gemini = genai.Client(api_key=k)
                        return cliente_gemini.chats.create(
                            model=m,
                            config=types.GenerateContentConfig(system_instruction=instrucoes, tools=gemini_tools)
                        )
                    else:
                        return [{"role": "system", "content": instrucoes}]

                motor_ia = inicializar_ia(provedor, api_key, modelo)

                console.print(f"Conectado via {provedor.upper()} ({modelo})\n")

                while True:
                    try:
                        user_input = await pedir_entrada()
                    except (KeyboardInterrupt, EOFError):
                        console.print("\nDesligando o TuxAssist... Até logo!")
                        break

                    cmd_bruto = user_input.strip()
                    cmd_baixo = cmd_bruto.lower()

                    if cmd_baixo in ["/sair", "sair", "exit", "quit"]:
                        console.print("Desligando o TuxAssist... Até logo!")
                        break

                    elif cmd_baixo in ["/clear", "clear", "limpar"]:
                        os.system("cls" if os.name == "nt" else "clear")
                        banner(provedor, modelo)
                        continue

                    elif cmd_baixo in ["/ls", "ls"]:
                        os.system("dir" if os.name == "nt" else "ls --color=auto")
                        print()
                        continue

                    elif cmd_baixo == "/mu":
                        provedor, api_key, modelo = setup_ia(config, mudar_agora=True)
                        motor_ia = inicializar_ia(provedor, api_key, modelo)
                        os.system("cls" if os.name == "nt" else "clear")
                        banner(provedor, modelo)
                        console.print(f"Trocado para {provedor.upper()} ({modelo})\n")
                        continue

                    elif cmd_bruto.startswith("!"):
                        comando_manual = cmd_bruto[1:].strip()
                        is_valid, msg = validate_command(comando_manual)
                        if not is_valid:
                            console.print(f"Erro de Segurança: {msg}")
                        else:
                            os.system(comando_manual)
                        print()
                        continue

                    if not cmd_bruto:
                        continue

                    texto_final = ""
                    max_iterations = 5

                    try:
                        if provedor == "gemini":
                            response = await asyncio.to_thread(motor_ia.send_message, user_input)
                            it = 0
                            while response.function_calls and it < max_iterations:
                                it += 1
                                if it >= max_iterations:
                                    console.print("[yellow]⚠️ Limite máximo de iterações de ferramentas atingido (5). Parando execução para evitar loops infinitos.[/yellow]")
                                    break

                                respostas_das_ferramentas = []
                                for fc in response.function_calls:
                                    if fc.name not in valid_tool_names:
                                        texto_resultado = f"Erro: Ferramenta '{fc.name}' não existe."
                                    else:
                                        mostrar_ferramenta(fc.name, fc.args)
                                        try:
                                            args_dict = dict(fc.args) if fc.args else {}
                                            resultado_mcp = await session.call_tool(fc.name, arguments=args_dict)
                                            texto_resultado = resultado_mcp.content[0].text if resultado_mcp.content else "Sem resultado."
                                        except Exception as erro_mcp:
                                            texto_resultado = f"Erro na execução da ferramenta MCP: {erro_mcp}"
                                    
                                    mostrar_resultado(texto_resultado)
                                    respostas_das_ferramentas.append(
                                        types.Part.from_function_response(
                                            name=fc.name,
                                            response={"result": limitar_texto(texto_resultado)}
                                        )
                                    )
                                response = await asyncio.to_thread(motor_ia.send_message, respostas_das_ferramentas)
                            texto_final = response.text or "Sem resposta."

                        else:
                            motor_ia.append({"role": "user", "content": user_input})
                            motor_ia = compactar_historico(motor_ia)

                            url = "https://api.groq.com/openai/v1/chat/completions" if provedor == "groq" else "https://api.openai.com/v1/chat/completions"
                            headers = {
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json",
                                "User-Agent": "TuxAssist-Web-Client"
                            }
                            payload = {"model": modelo, "messages": motor_ia, "tools": openai_tools, "tool_choice": "auto"}

                            resposta_json = await chamar_api_com_retry(url, headers, payload)
                            msg = resposta_json["choices"][0]["message"]

                            it = 0
                            while msg.get("tool_calls") and it < max_iterations:
                                it += 1
                                if it >= max_iterations:
                                    console.print("[yellow]⚠️ Limite máximo de iterações de ferramentas atingido (5). Parando execução para evitar loops infinitos.[/yellow]")
                                    break

                                motor_ia.append(msg)
                                for fc in msg["tool_calls"]:
                                    f_name = fc["function"]["name"]
                                    f_args_str = fc["function"]["arguments"]

                                    if f_name not in valid_tool_names:
                                        texto_resultado = f"Erro: Ferramenta '{f_name}' não existe."
                                    else:
                                        mostrar_ferramenta(f_name, f_args_str)
                                        try:
                                            args = json.loads(f_args_str) if f_args_str else {}
                                            resultado_mcp = await session.call_tool(f_name, arguments=args)
                                            texto_resultado = resultado_mcp.content[0].text if resultado_mcp.content else "Sem resultado."
                                        except Exception as erro_mcp:
                                            texto_resultado = f"Erro na execução da ferramenta MCP: {erro_mcp}"

                                    mostrar_resultado(texto_resultado)

                                    motor_ia.append({
                                        "role": "tool",
                                        "tool_call_id": fc["id"],
                                        "name": f_name,
                                        "content": limitar_texto(texto_resultado)
                                    })

                                payload["messages"] = motor_ia
                                resposta_json = await chamar_api_com_retry(url, headers, payload)
                                msg = resposta_json["choices"][0]["message"]

                            texto_final = msg.get("content", "")
                            if texto_final:
                                motor_ia.append({"role": "assistant", "content": texto_final})

                    except Exception as e:
                        texto_final = f"❌ Erro na execução: {e}"

                    if texto_final:
                        mostrar_resposta(texto_final)

    except Exception as server_err:
        console.print(f"Erro ao iniciar ou manter conexão com o servidor MCP: {server_err}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTuxAssist encerrado.")

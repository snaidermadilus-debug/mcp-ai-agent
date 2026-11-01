import os
import json
import shutil
import asyncio
import urllib.request
import urllib.error
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich import box

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Falta a biblioteca do Gemini! Rode: python -m pip install google-genai rich")
    exit()

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
    print("⚠️  prompt_toolkit não instalado: usando entrada simples.")
    print("   Para a caixa completa, rode: python -m pip install prompt_toolkit\n")

try:
    import readline
except ImportError:
    pass

console = Console()

LARANJA = "#d97757"
CINZA = "grey50"
C_LARANJA = "\033[38;2;217;119;87m"
C_CINZA = "\033[90m"
C_RESET = "\033[0m"

CONFIG_FILE = "tuxassist_config.json"
LIMITE_TOKENS_FERRAMENTA = 4000


def limitar_para_ia(texto, limite=LIMITE_TOKENS_FERRAMENTA):
    """Corta a saída antes de mandar pra API, pra não estourar a cota de tokens por minuto."""
    texto = texto or ""
    if len(texto) <= limite:
        return texto
    cortado = len(texto) - limite
    return texto[:limite] + f"\n\n[...saída cortada, {cortado} caracteres a mais omitidos...]"


def carregar_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}


def salvar_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def banner(provedor=None, modelo=None):
    linhas = f"[bold {LARANJA}]✻ Bem-vindo ao TuxAssist[/]\n\n"
    linhas += f"[{CINZA}]/mu trocar IA · /clear limpar · /ls listar · !cmd rodar · /sair[/]"
    if provedor and modelo:
        linhas += f"\n\n[{CINZA}]modelo:[/] {provedor.upper()} · {modelo}\n"
        linhas += f"[{CINZA}]cwd:[/] {os.getcwd()}"
    console.print(Panel.fit(linhas, border_style=LARANJA, box=box.ROUNDED, padding=(1, 2)))
    console.print()


def titulo(texto):
    console.print(f"\n[{LARANJA}]●[/] [bold]{texto}[/]")


def opcao(n, texto):
    console.print(f"  [{CINZA}]{n})[/] {texto}")


def setup_ia(config, mudar_agora=False):
    os.system("clear")
    banner()

    p_salvo = config.get("provedor_atual")
    m_salvo = config.get("modelo_atual")

    if not mudar_agora and p_salvo and m_salvo and config.get(f"{p_salvo}_key"):
        console.print(f"[{LARANJA}]●[/] Sessão anterior encontrada")
        console.print(f"  [{CINZA}]⎿  Provedor: {p_salvo.upper()}[/]")
        console.print(f"  [{CINZA}]⎿  Modelo:   {m_salvo}[/]")
        resp = Prompt.ask(f"\n[{LARANJA}]?[/] Reconectar com essa configuração? (S/n)", default="s").strip().lower()
        if resp == "s":
            return p_salvo, config[f"{p_salvo}_key"], m_salvo

    titulo("Escolha o motor de Inteligência Artificial")
    opcao(1, "Gemini (Google)")
    opcao(2, "Groq (Llama, Mixtral - Ultra rápido)")
    opcao(3, "OpenAI (ChatGPT)")

    provedor = ""
    while True:
        op = Prompt.ask(f"\n[{LARANJA}]>[/] Opção (1 a 3)")
        if op == '1': provedor = "gemini"; break
        if op == '2': provedor = "groq"; break
        if op == '3': provedor = "openai"; break

    chave_salva = config.get(f"{provedor}_key", "")
    if chave_salva:
        k = Prompt.ask(f"\n[green]✔[/] Chave {provedor.capitalize()} salva! ENTER para usar a mesma ou cole uma nova", default="", show_default=False)
        api_key = k.strip() if k.strip() else chave_salva
    else:
        api_key = Prompt.ask(f"\n[{LARANJA}]>[/] Cole sua API Key da {provedor.capitalize()}").strip()

    titulo(f"Escolha o modelo da {provedor.capitalize()}")
    modelo = ""

    if provedor == "gemini":
        opcao(1, "gemini-3.5-flash (Recomendado)")
        opcao(2, "gemini-3.5-flash-lite")
        opcao(3, "gemini-2.5-pro")
        opcao(4, "Digitar outro nome")
        op = Prompt.ask(f"[{LARANJA}]>[/] Opção")
        if op == '1': modelo = "gemini-3.5-flash"
        elif op == '2': modelo = "gemini-3.5-flash-lite"
        elif op == '3': modelo = "gemini-2.5-pro"
        else: modelo = Prompt.ask(f"[{LARANJA}]>[/] Nome do modelo").strip()

    elif provedor == "groq":
        opcao(1, "llama-3.3-70b-versatile (Recomendado)")
        opcao(2, "mixtral-8x7b-32768")
        opcao(3, "openai/gpt-oss-120b")
        opcao(4, "Digitar outro nome")
        op = Prompt.ask(f"[{LARANJA}]>[/] Opção")
        if op == '1': modelo = "llama-3.3-70b-versatile"
        elif op == '2': modelo = "mixtral-8x7b-32768"
        elif op == '3': modelo = "openai/gpt-oss-120b"
        else: modelo = Prompt.ask(f"[{LARANJA}]>[/] Nome do modelo").strip()

    elif provedor == "openai":
        opcao(1, "gpt-4o (Recomendado)")
        opcao(2, "gpt-4o-mini")
        opcao(3, "Digitar outro nome")
        op = Prompt.ask(f"[{LARANJA}]>[/] Opção")
        if op == '1': modelo = "gpt-4o"
        elif op == '2': modelo = "gpt-4o-mini"
        else: modelo = Prompt.ask(f"[{LARANJA}]>[/] Nome do modelo").strip()

    config[f"{provedor}_key"] = api_key
    config["provedor_atual"] = provedor
    config["modelo_atual"] = modelo
    salvar_config(config)

    return provedor, api_key, modelo


def chamar_api_direta(provedor, api_key, modelo, mensagens, tools=None):
    url = "https://api.groq.com/openai/v1/chat/completions" if provedor == "groq" else "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    }
    payload = {"model": modelo, "messages": mensagens}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))


async def pedir_entrada():
    """ENTER envia. ALT+ENTER (ou ESC e depois ENTER) cria nova linha."""
    if not TEM_PT:
        largura = shutil.get_terminal_size((80, 20)).columns
        linha = f"{C_CINZA}{'─' * largura}{C_RESET}"
        print(linha)
        try:
            texto = input(f"\001{C_LARANJA}\002>\001{C_RESET}\002 ")
        finally:
            print(linha)
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
    texto = await app.run_async()
    print()
    return texto or ""


def mostrar_ferramenta(nome, args):
    try:
        if isinstance(args, str):
            args = json.loads(args)
        partes = ", ".join(f"{k}={repr(v)[:60]}" for k, v in dict(args).items())
    except Exception:
        partes = str(args)[:80]
    t = Text()
    t.append("● ", style=LARANJA)
    t.append(nome, style="bold")
    t.append(f"({partes})")
    console.print(t)


def mostrar_resultado(texto, max_linhas=4):
    linhas = (texto or "").strip().splitlines() or ["(sem saída)"]
    for i, l in enumerate(linhas[:max_linhas]):
        prefixo = "  ⎿  " if i == 0 else "     "
        console.print(Text(f"{prefixo}{l[:150]}", style=CINZA))
    if len(linhas) > max_linhas:
        console.print(Text(f"     … +{len(linhas) - max_linhas} linhas", style=CINZA))


def mostrar_resposta(texto):
    grade = Table.grid(padding=(0, 1))
    grade.add_column(width=1)
    grade.add_column()
    grade.add_row(f"[{LARANJA}]●[/]", Markdown(texto or ""))
    console.print(grade)
    console.print()


async def main():
    config = carregar_config()
    provedor, api_key, modelo = setup_ia(config)

    os.system("clear")
    banner(provedor, modelo)
    console.print(f"[{CINZA}]Conectando ao servidor MCP e preparando ferramentas...[/]")

    server_params = StdioServerParameters(command="python", args=["servidor_mcp.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()

            gemini_tools = [{"function_declarations": [
                {"name": t.name, "description": t.description, "parameters": t.input_schema}
                for t in mcp_tools.tools
            ]}]

            openai_tools = [{"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.input_schema
            }} for t in mcp_tools.tools]

            instrucoes = (
                "Você é o TuxAssist, um assistente com acesso TOTAL ao terminal Termux do usuário.\n"
                "REGRAS CLARAS PARA FERRAMENTAS:\n"
                "- Para ler pastas, use 'listar_arquivos'.\n"
                "- Para ler códigos, use 'ler_arquivo'.\n"
                "- Para rodar comandos, USE a ferramenta 'executar_comando' você mesmo!"
            )

            cliente_gemini = None

            def inicializar_ia(p, k, m):
                nonlocal cliente_gemini
                if p == "gemini":
                    cliente_gemini = genai.Client(api_key=k)
                    return cliente_gemini.chats.create(
                        model=m,
                        config=types.GenerateContentConfig(system_instruction=instrucoes, tools=gemini_tools)
                    )
                else:
                    return [{"role": "system", "content": instrucoes}]

            motor_ia = inicializar_ia(provedor, api_key, modelo)

            print("\a", end="")
            console.print(f"[{LARANJA}]●[/] Conectado via [bold]{provedor.upper()}[/] ([{CINZA}]{modelo}[/])\n")

            while True:
                try:
                    user_input = await pedir_entrada()
                except (KeyboardInterrupt, EOFError):
                    console.print(f"\n[{LARANJA}]✻[/] Desligando o TuxAssist... Falou!")
                    break

                cmd_bruto = user_input.strip()
                cmd_baixo = cmd_bruto.lower()

                if cmd_baixo in ["/sair", "sair", "exit", "quit"]:
                    console.print(f"[{LARANJA}]✻[/] Desligando o TuxAssist... Falou!")
                    break

                elif cmd_baixo in ["/clear", "clear", "limpar"]:
                    os.system("clear")
                    banner(provedor, modelo)
                    continue

                elif cmd_baixo in ["/ls", "ls"]:
                    os.system("ls --color=auto")
                    print()
                    continue

                elif cmd_baixo == "/mu":
                    provedor, api_key, modelo = setup_ia(config, mudar_agora=True)
                    motor_ia = inicializar_ia(provedor, api_key, modelo)
                    os.system("clear")
                    banner(provedor, modelo)
                    print("\a", end="")
                    console.print(f"[{LARANJA}]●[/] Trocado para [bold]{provedor.upper()}[/] ([{CINZA}]{modelo}[/])\n")
                    continue

                elif cmd_bruto.startswith("!"):
                    os.system(cmd_bruto[1:].strip())
                    print()
                    continue

                if not cmd_bruto:
                    continue

                texto_final = ""

                with console.status(f"[{LARANJA}]Pensando…[/] [{CINZA}](Ctrl+C para interromper)[/]",
                                    spinner="dots", spinner_style=LARANJA) as status:
                    try:
                        if provedor == "gemini":
                            response = motor_ia.send_message(user_input)
                            while response.function_calls:
                                respostas_das_ferramentas = []
                                for fc in response.function_calls:
                                    mostrar_ferramenta(fc.name, fc.args)
                                    try:
                                        resultado_mcp = await session.call_tool(fc.name, arguments=fc.args)
                                        texto_resultado = resultado_mcp.content[0].text
                                    except Exception as erro_mcp:
                                        texto_resultado = f"Erro na ferramenta: {erro_mcp}"
                                    mostrar_resultado(texto_resultado)
                                    respostas_das_ferramentas.append(
                                        types.Part.from_function_response(
                                            name=fc.name,
                                            response={"result": limitar_para_ia(texto_resultado)}
                                        )
                                    )
                                status.update(f"[{LARANJA}]Analisando dados do Termux…[/]")
                                response = motor_ia.send_message(respostas_das_ferramentas)
                            texto_final = response.text

                        else:
                            motor_ia.append({"role": "user", "content": user_input})
                            resposta_json = chamar_api_direta(provedor, api_key, modelo, motor_ia, openai_tools)
                            msg = resposta_json["choices"][0]["message"]

                            while msg.get("tool_calls"):
                                motor_ia.append(msg)
                                for fc in msg["tool_calls"]:
                                    f_name = fc["function"]["name"]
                                    f_args = fc["function"]["arguments"]
                                    mostrar_ferramenta(f_name, f_args)

                                    try:
                                        args = json.loads(f_args)
                                        resultado_mcp = await session.call_tool(f_name, arguments=args)
                                        texto_resultado = resultado_mcp.content[0].text
                                    except Exception as erro_mcp:
                                        texto_resultado = f"Erro na ferramenta: {erro_mcp}"

                                    mostrar_resultado(texto_resultado)

                                    motor_ia.append({
                                        "role": "tool",
                                        "tool_call_id": fc["id"],
                                        "name": f_name,
                                        "content": limitar_para_ia(texto_resultado)
                                    })

                                status.update(f"[{LARANJA}]Analisando dados do Termux…[/]")
                                resposta_json = chamar_api_direta(provedor, api_key, modelo, motor_ia, openai_tools)
                                msg = resposta_json["choices"][0]["message"]

                            texto_final = msg.get("content", "")
                            if texto_final:
                                motor_ia.append({"role": "assistant", "content": texto_final})

                    except urllib.error.HTTPError as he:
                        texto_final = f"❌ Erro na API HTTP ({he.code}): {he.read().decode('utf-8')}"
                    except KeyboardInterrupt:
                        console.print(Text("  ⎿  Interrompido", style=CINZA))
                        texto_final = ""
                    except Exception as e:
                        texto_final = f"❌ Erro interno: {e}"

                if texto_final:
                    mostrar_resposta(texto_final)


if __name__ == "__main__":
    asyncio.run(main())

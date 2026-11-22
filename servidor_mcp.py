import os
import subprocess
from config import get_active_workspace
from security import is_path_safe, classify_command

class ServidorMCP:
    """Servidor MCP (Model Context Protocol) para gerenciamento de ferramentas do agente."""

    def __init__(self):
        self.tools = {
            "listar_arquivos": self.listar_arquivos,
            "ler_arquivo": self.ler_arquivo,
            "executar_comando": self.executar_comando,
            "comando_remoto_esp32": self.comando_remoto_esp32
        }

    def get_tool_definitions(self) -> list:
        return [
            {
                "name": "listar_arquivos",
                "description": "Lista todos os arquivos de um diretório e vasculha DENTRO de todas as subpastas automaticamente.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "pasta": {"type": "STRING", "description": "Caminho da pasta (padrão '.')"}
                    }
                }
            },
            {
                "name": "ler_arquivo",
                "description": "Lê e retorna o conteúdo de um arquivo de texto no workspace.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "arquivo": {"type": "STRING", "description": "Caminho do arquivo"}
                    },
                    "required": ["arquivo"]
                }
            },
            {
                "name": "executar_comando",
                "description": "Executa um comando no terminal do sistema e retorna a saída.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "comando": {"type": "STRING", "description": "Comando de terminal a executar"},
                        "confirmed": {"type": "BOOLEAN", "description": "Se o comando foi explicitamente confirmado pelo usuário"}
                    },
                    "required": ["comando"]
                }
            },
            {
                "name": "comando_remoto_esp32",
                "description": "Acessa o ESP32-S3 via rede local (Socket TCP) e executa um comando nele.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "comando": {"type": "STRING", "description": "Comando para o ESP32"}
                    },
                    "required": ["comando"]
                }
            }
        ]

    def executar_ferramenta(self, nome: str, args: dict) -> str:
        args = args or {}
        if nome in self.tools:
            try:
                return self.tools[nome](**args)
            except Exception as e:
                return f"Erro na execução da ferramenta {nome}: {str(e)}"
        return f"Ferramenta desconhecida: {nome}"

    def listar_arquivos(self, pasta: str = ".") -> str:
        workspace = get_active_workspace()
        target_dir = os.path.normpath(os.path.join(workspace, pasta))
        
        if not is_path_safe(target_dir, workspace):
            return f"Erro de segurança: Acesso negado. O caminho '{pasta}' está fora do diretório autorizado ({workspace})."
        
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            return f"Diretório não encontrado: {pasta}"

        resultado = []
        for root, dirs, files in os.walk(target_dir):
            # Ignora pastas ocultas e node_modules
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'dist')]
            for file in files:
                if file.startswith('.'):
                    continue
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, workspace)
                resultado.append(rel_p)
                if len(resultado) >= 300:
                    break
            if len(resultado) >= 300:
                break

        if not resultado:
            return "A pasta está vazia."
        
        texto = "\n".join(resultado)
        if len(resultado) >= 300:
            texto += "\n\n[...lista cortada em 300 arquivos...]"
        return texto

    def ler_arquivo(self, arquivo: str) -> str:
        if not arquivo:
            return "Erro: arquivo não especificado."
        workspace = get_active_workspace()
        full_path = os.path.normpath(os.path.join(workspace, arquivo))
        
        if not is_path_safe(full_path, workspace):
            return f"Erro de segurança: Acesso negado. O arquivo '{arquivo}' está fora do diretório autorizado ({workspace})."
        
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                return f"Erro ao ler arquivo: {e}"
        return f"Arquivo não encontrado: {arquivo}"

    def executar_comando(self, comando: str, confirmed: bool = False) -> str:
        if not comando:
            return "Erro: comando não especificado."
        
        workspace = get_active_workspace()
        sec = classify_command(comando)
        
        if sec["risk_level"] >= 2 and not confirmed:
            import urllib.parse
            cmd_enc = urllib.parse.quote(comando)
            reason_enc = urllib.parse.quote(sec["reason"])
            return f"⚠️ ALERTA DE SEGURANÇA (Nível 2): O comando abaixo requer sua autorização:\n{comando}\n\n[CONFIRMATION_REQUIRED:2:{cmd_enc}:{reason_enc}]"

        try:
            res = subprocess.run(
                comando,
                shell=True,
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15
            )
            saida = (res.stdout or "") + (res.stderr or "")
            return saida.strip() if saida.strip() else "Comando executado com sucesso (sem saída de texto)."
        except subprocess.TimeoutExpired:
            return "Erro: O comando excedeu o tempo limite de execução (15 segundos)."
        except Exception as e:
            return f"Erro ao executar comando: {e}"

    def comando_remoto_esp32(self, comando: str) -> str:
        return f'[Simulação ESP32] Comando enviado com sucesso para 192.168.0.100:2222 -> "{comando}". Resposta: OK (Modo Termux / Python)'

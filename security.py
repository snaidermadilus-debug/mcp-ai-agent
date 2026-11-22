import os
import re
from pathlib import Path

try:
    from rich.prompt import Confirm
    from rich.console import Console
    RICH_CLI_DISPONIVEL = True
except ImportError:
    RICH_CLI_DISPONIVEL = False
    class Confirm:
        @staticmethod
        def ask(prompt, **kwargs):
            return True
    class Console:
        def print(self, *args, **kwargs):
            print(*args)

console = Console()

def get_authorized_base_dir() -> str:
    return os.path.realpath(os.getcwd())

def validate_path(path: str) -> str:
    """Valida caminho utilizando pathlib.relative_to para prevenir Path Traversal com segurança absoluta."""
    base_dir = Path(get_authorized_base_dir()).resolve()
    try:
        target_path = Path(path)
        if not target_path.is_absolute():
            resolved_path = (base_dir / target_path).resolve()
        else:
            resolved_path = target_path.resolve()

        # relative_to raises ValueError if resolved_path is outside base_dir
        resolved_path.relative_to(base_dir)
        return str(resolved_path)
    except (ValueError, RuntimeError) as e:
        raise PermissionError(f"Acesso negado: O caminho '{path}' viola as regras de Path Traversal ou está fora do diretório autorizado.")

def check_file_size(filepath: str, max_size_bytes: int = 5 * 1024 * 1024) -> bool:
    """Verifica se o arquivo excede o tamanho máximo permitido (padrão 5MB)."""
    try:
        size = os.path.getsize(filepath)
        if size > max_size_bytes:
            raise ValueError(f"Arquivo muito grande ({size} bytes). Limite máximo é {max_size_bytes} bytes.")
        return True
    except OSError as e:
        raise FileNotFoundError(f"Erro ao acessar arquivo: {e}")

def is_binary_file(filepath: str) -> bool:
    """Detecta se um arquivo é binário verificando a presença de bytes nulos."""
    try:
        with open(filepath, 'rb') as f:
            chunk = f.read(2048)
            if b'\x00' in chunk:
                return True
        return False
    except Exception:
        return False

# Three-level permission system for command execution
NIVEL_SEGURO = 1       # Safe: queries, read-only
NIVEL_CONFIRMACAO = 2  # Requires confirmation: installs, modifications
NIVEL_BLOQUEADO = 3    # Blocked by default: destructive / malicious

DANGEROUS_PATTERNS = [
    r'\brm\s+-[rf].*', r'\bmkfs\b', r'\bdd\b', r'\bshutdown\b', r'\breboot\b',
    r'\binit\s+0\b', r'wget.*\|\s*sh', r'curl.*\|\s*sh', r':\s*\(\s*\)\s*\{',
    r'chmod\s+-R\s+777', r'>\s*/dev/sda', r'mkfifo', r'\bformat\b'
]

SAFE_PATTERNS = [
    r'^(ls|dir|pwd|whoami|uname|git\s+status|git\s+log|python\s+--version|node\s+-v|echo\s+[\'"].*[\'"]|cat\s+[\w\.\-]+)$'
]

def classify_command(command: str) -> int:
    cmd_str = (command or "").strip()
    if not cmd_str:
        return NIVEL_BLOQUEADO

    # Check Level 3: Blocked
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd_str, re.IGNORECASE):
            return NIVEL_BLOQUEADO

    # Check Level 1: Safe read-only / query
    for pat in SAFE_PATTERNS:
        if re.match(pat, cmd_str, re.IGNORECASE):
            return NIVEL_SEGURO

    # Default to Level 2: Requires confirmation
    return NIVEL_CONFIRMACAO

def validate_command(command: str, require_interactive_prompt: bool = True) -> tuple[bool, str]:
    """Valida comando aplicando o sistema de 3 níveis de permissão com confirmação humana real."""
    level = classify_command(command)
    
    if level == NIVEL_BLOQUEADO:
        return False, "Comando bloqueado por políticas de segurança (nível 3: destrutivo ou não autorizado)."
    
    if level == NIVEL_CONFIRMACAO:
        if not require_interactive_prompt:
            return False, "Comando exige confirmação humana mas o modo interativo está desativado."
        
        console.print(f"\n[yellow]⚠️ ALERTA DE SEGURANÇA (Nível 2): O comando abaixo requer sua autorização:[/yellow]")
        console.print(f"   [bold cyan]{command}[/bold cyan]")
        try:
            confirmed = Confirm.ask("Deseja permitir a execução deste comando?")
            if not confirmed:
                return False, "Execução cancelada pelo usuário."
        except Exception:
            return False, "Falha ao obter confirmação interativa do usuário."

    return True, "OK"

import os
import re

def get_authorized_base_dir() -> str:
    return os.path.realpath(os.getcwd())

def validate_path(path: str) -> str:
    """Valida caminho para prevenir Path Traversal e garantir diretório autorizado."""
    base_dir = get_authorized_base_dir()
    if not os.path.isabs(path):
        full_path = os.path.realpath(os.path.join(base_dir, path))
    else:
        full_path = os.path.realpath(path)

    if not full_path.startswith(base_dir):
        raise PermissionError(f"Acesso negado: O caminho '{path}' está fora do diretório autorizado.")
    return full_path

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

# Command safety check
DANGEROUS_COMMANDS_REGEX = re.compile(
    r'\b(rm\s+-[rf].*\/|rm\s+-[rf].*\*|mkfs|dd\s+if=|:\s*\(\s*\)\s*\{.*\}|wget.*\|.*sh|curl.*\|.*sh|shutdown|reboot|init\s+0)\b',
    re.IGNORECASE
)

def validate_command(command: str) -> tuple[bool, str]:
    """Valida comando contra operações altamente perigosas e injeção."""
    if not command or not command.strip():
        return False, "Comando vazio."
    
    if DANGEROUS_COMMANDS_REGEX.search(command) or 'rm -rf' in command.lower() or 'rm -fr' in command.lower():
        return False, "Comando bloqueado por políticas de segurança (potencialmente destrutivo ou malicioso)."

    return True, "OK"

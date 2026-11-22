import os
import pathlib

def is_path_safe(target_path: str, base_dir: str) -> bool:
    """Valida se target_path está dentro de base_dir, prevenindo Path Traversal e validando symlinks."""
    try:
        resolved_base = os.path.realpath(os.path.abspath(base_dir))
        resolved_target = os.path.realpath(os.path.abspath(os.path.join(resolved_base, target_path)))
        
        # Verifica se o caminho resolvido está dentro da base resolvida
        common = os.path.commonpath([resolved_base, resolved_target])
        return common == resolved_base
    except Exception:
        return false

def classify_command(cmd: str) -> dict:
    """Classifica o nível de risco de um comando de terminal."""
    trimmed = (cmd or "").strip().lower()
    
    dangerous_keywords = [
        "rm ", " rm ", "sudo", "su ", "python3 -c", "python -c", "eval",
        "bash -c", "sh -c", "dd if=", "mkfs", "chmod 777", "chown"
    ]
    
    if any(kw in trimmed for kw in dangerous_keywords) or trimmed.startswith("rm "):
        return {
            "risk_level": 2,
            "reason": "Comando potencialmente perigoso ou de execução direta no sistema (ex: exclusão, sudo, python -c)."
        }
    
    warning_keywords = ["apt", "pip", "npm install", "wget", "curl", "kill"]
    if any(trimmed.startswith(kw) for kw in warning_keywords):
        return {
            "risk_level": 1,
            "reason": "Comando de modificação de sistema ou download de rede."
        }
    
    return {
        "risk_level": 0,
        "reason": "Comando seguro de leitura ou navegação."
    }

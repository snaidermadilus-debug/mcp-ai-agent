import os
import json
import pathlib

CONFIG_FILE = "tuxassist_config.json"

def load_config() -> dict:
    """Carrega as configurações salvas em tuxassist_config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Aviso] Erro ao carregar {CONFIG_FILE}: {e}")
    return {}

def save_config(config_data: dict) -> dict:
    """Salva as configurações em tuxassist_config.json."""
    existing = load_config()
    existing.update(config_data)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Erro] Falha ao salvar {CONFIG_FILE}: {e}")
    return existing

def get_active_workspace() -> str:
    """Retorna o diretório de trabalho ativo validado."""
    config = load_config()
    ws = config.get("workspace_dir")
    if ws:
        target = os.path.expanduser(str(ws).strip())
        resolved = os.path.abspath(target)
        if os.path.exists(resolved) and os.path.isdir(resolved):
            try:
                os.listdir(resolved)
                return resolved
            except PermissionError:
                print(f"[Aviso] Sem permissão para acessar o workspace configurado: {resolved}")
        else:
            print(f"[Aviso] Workspace configurado inválido ou inexistente: {resolved}")
    
    return os.path.abspath(os.getcwd())

def set_active_workspace(path_str: str) -> tuple[bool, str]:
    """Define e valida um novo diretório de trabalho."""
    if not path_str or not isinstance(path_str, str):
        return False, "Caminho não especificado."
    
    target = os.path.expanduser(path_str.strip())
    resolved = os.path.abspath(target)
    
    if not os.path.exists(resolved):
        return False, f"✗ Diretório inválido.\n\nA pasta informada não existe ({resolved}).\nA configuração anterior foi preservada."
    
    if not os.path.isdir(resolved):
        return False, f"✗ Diretório inválido.\n\nO caminho informado não é um diretório ({resolved}).\nA configuração anterior foi preservada."
    
    try:
        os.listdir(resolved)
    except PermissionError:
        return False, f"✗ Diretório inválido.\n\nSem permissão para acessar o diretório ({resolved}).\nA configuração anterior foi preservada."
    
    save_config({"workspace_dir": resolved})
    success_msg = f"✓ Diretório padrão atualizado!\n\n{resolved}\n\nAs próximas operações utilizarão esse diretório."
    return True, success_msg

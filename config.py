import os
import json
import stat

CONFIG_FILE = "tuxassist_config.json"
MAX_HISTORY_MESSAGES = 50
LIMITE_TOKENS_FERRAMENTA = 4000

def carregar_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def salvar_config(config: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        # Restrict file permissions to owner only (chmod 600)
        if os.name != 'nt':
            os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        print(f"⚠️  Aviso ao salvar configurações: {e}")

def mascarar_chave(api_key: str) -> str:
    """Retorna uma versão mascarada da API Key para logs e exibição segura."""
    if not api_key or len(api_key) < 8:
        return "***"
    return api_key[:4] + "..." + api_key[-4:]

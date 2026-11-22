import os
import subprocess
import socket
import sys

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    print("❌ Erro Crítico: O pacote 'mcp' (Model Context Protocol) não está instalado ou é incompatível.", file=sys.stderr)
    print("   Instale as dependências executando: python3 -m pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

from security import validate_path, check_file_size, is_binary_file, validate_command

mcp = MCPServer("TuxServer")

@mcp.tool()
def listar_arquivos(pasta: str = ".") -> str:
    """Lista todos os arquivos de um diretório autorizado e subpastas automaticamente."""
    try:
        target_dir = validate_path(pasta)
        resultado = []
        for raiz, diretorios, arquivos in os.walk(target_dir):
            diretorios[:] = [d for d in diretorios if not d.startswith('.') and d != '__pycache__' and d != 'node_modules' and d != 'dist']
            for arquivo in arquivos:
                if not arquivo.startswith('.'):
                    caminho_completo = os.path.join(raiz, arquivo)
                    rel_path = os.path.relpath(caminho_completo, os.getcwd())
                    resultado.append(rel_path)
                    if len(resultado) >= 300:
                        break
            if len(resultado) >= 300:
                break

        if not resultado:
            return "A pasta está vazia ou inacessível."
        texto = "\n".join(resultado)
        if len(resultado) >= 300:
            texto += "\n\n[...lista cortada em 300 arquivos...]"
        return texto
    except Exception as e:
        return f"Erro ao listar pasta: {e}"

@mcp.tool()
def ler_arquivo(arquivo: str) -> str:
    """Lê e retorna o conteúdo de um arquivo de texto autorizado."""
    try:
        target_path = validate_path(arquivo)
        if not os.path.exists(target_path) or not os.path.isfile(target_path):
            return f"Erro: Arquivo não encontrado ou inválido: {arquivo}"
        
        if is_binary_file(target_path):
            return f"Erro: O arquivo '{arquivo}' parece ser binário e não pode ser lido como texto."
        
        check_file_size(target_path, 2 * 1024 * 1024) # 2MB limit

        with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"

@mcp.tool()
def executar_comando(comando: str) -> str:
    """Executa um comando no terminal do sistema com validação de segurança e timeout."""
    is_valid, msg = validate_command(comando)
    if not is_valid:
        return f"Erro de Segurança: {msg}"

    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.getcwd()
        )
        saida = resultado.stdout + resultado.stderr
        exit_code = resultado.returncode
        
        status_msg = f"[Exit Code: {exit_code}]"
        output_final = saida if saida.strip() else "Comando executado com sucesso (sem saída)."
        return f"{output_final}\n{status_msg}"
    
    except subprocess.TimeoutExpired:
        return f"Erro: O comando '{comando}' excedeu o tempo limite de execução (15 segundos) e foi interrompido."
    except Exception as e:
        return f"Erro fatal ao executar comando: {e}"

@mcp.tool()
def comando_remoto_esp32(comando: str, ip: str = "192.168.0.100", porta: int = 2222) -> str:
    """Acessa o ESP32-S3 via rede local (Socket TCP) com timeout e fechamento garantido."""
    if not comando or len(comando.strip()) == 0:
        return "Erro: Comando ESP32 vazio."

    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((ip, porta))
        
        try:
            s.recv(1024)
        except socket.timeout:
            pass

        s.sendall((comando.strip() + "\n").encode('utf-8'))
        resposta = s.recv(4096).decode('utf-8', errors='replace')
        return resposta.strip() if resposta.strip() else "Comando enviado ao ESP32 com sucesso."

    except socket.timeout:
        return f"Falha: Timeout ao conectar no ESP32 em {ip}:{porta}."
    except Exception as e:
        return f"Falha ao conectar no ESP32: {e}"
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass

if __name__ == "__main__":
    mcp.run()

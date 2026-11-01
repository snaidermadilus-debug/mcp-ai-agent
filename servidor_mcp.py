from mcp.server.mcpserver import MCPServer
import os
import subprocess
import socket

mcp = MCPServer("TuxServer")

@mcp.tool()
def listar_arquivos(pasta: str = ".") -> str:
    """Lista todos os arquivos de um diretório e vasculha DENTRO de todas as subpastas automaticamente."""
    try:
        resultado = []
        for raiz, diretorios, arquivos in os.walk(pasta):
            diretorios[:] = [d for d in diretorios if not d.startswith('.') and d != '__pycache__']
            for arquivo in arquivos:
                if not arquivo.startswith('.'):
                    caminho_completo = os.path.join(raiz, arquivo)
                    if caminho_completo.startswith("./"):
                        caminho_completo = caminho_completo[2:]
                    resultado.append(caminho_completo)
                    if len(resultado) >= 300:
                        break
            if len(resultado) >= 300:
                break

        if not resultado:
            return "A pasta está vazia."
        texto = "\n".join(resultado)
        if len(resultado) >= 300:
            texto += "\n\n[...lista cortada em 300 arquivos. Peça uma subpasta específica para ver mais...]"
        return texto
    except Exception as e:
        return f"Erro ao ler pasta: {e}"

@mcp.tool()
def ler_arquivo(arquivo: str) -> str:
    """Lê e retorna o conteúdo de um arquivo de texto no Termux."""
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Erro ao ler arquivo: {e}"

@mcp.tool()
def executar_comando(comando: str) -> str:
    """Executa um comando no terminal do Termux e retorna a saída. Útil para rodar scripts, compilar, etc."""
    try:
        resultado = subprocess.run(comando, shell=True, capture_output=True, text=True, timeout=15)
        saida = resultado.stdout + resultado.stderr
        return saida if saida.strip() else "Comando executado com sucesso (sem saída de texto na tela)."
    except subprocess.TimeoutExpired:
        return f"Comando '{comando}' iniciado com sucesso (está rodando em segundo plano)."
    except Exception as e:
        return f"Erro fatal ao executar comando: {e}"

@mcp.tool()
def comando_remoto_esp32(comando: str) -> str:
    """Acessa o ESP32-S3 via rede local (Socket TCP) e executa um comando nele."""
    ip_esp32 = "192.168.0.100"
    porta = 2222

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip_esp32, porta))
        s.recv(1024)
        s.sendall((comando + "\n").encode('utf-8'))
        resposta = s.recv(4096).decode('utf-8')
        s.close()
        return resposta.strip()

    except Exception as e:
        return f"Falha ao conectar no ESP32: {e}"

if __name__ == "__main__":
    mcp.run()

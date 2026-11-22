import unittest
import os
import tempfile
import shutil
from security import is_path_safe, classify_command
from config import save_config, load_config, set_active_workspace, get_active_workspace
from servidor_mcp import ServidorMCP

class TestTuxAssist(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_config = load_config()

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        save_config(self.old_config)

    def test_path_safety(self):
        base = self.test_dir
        # Arquivo seguro dentro da base
        sub_file = os.path.join(base, "test.txt")
        self.assertTrue(is_path_safe(sub_file, base))
        
        # Path traversal fora da base
        outside = os.path.join(base, "../outside.txt")
        self.assertFalse(is_path_safe(outside, base))

    def test_command_classification(self):
        # Nível 0 (Seguro)
        self.assertEqual(classify_command("ls -la")["risk_level"], 0)
        self.assertEqual(classify_command("python --version")["risk_level"], 0)

        # Nível 1 (Modificação/Rede)
        self.assertEqual(classify_command("pip install requests")["risk_level"], 1)
        self.assertEqual(classify_command("curl https://example.com")["risk_level"], 1)

        # Nível 2 (Perigoso)
        self.assertEqual(classify_command("rm -rf /")["risk_level"], 2)
        self.assertEqual(classify_command("sudo reboot")["risk_level"], 2)
        self.assertEqual(classify_command("python -c 'import os; os.system(\"ls\")'")["risk_level"], 2)

    def test_config_and_workspace(self):
        success, msg = set_active_workspace(self.test_dir)
        self.assertTrue(success)
        self.assertEqual(get_active_workspace(), os.path.abspath(self.test_dir))

        # Tentar definir diretório inválido
        success_invalid, _ = set_active_workspace("/non/existent/path/xyz")
        self.assertFalse(success_invalid)

    def test_mcp_tools(self):
        set_active_workspace(self.test_dir)
        mcp = ServidorMCP()

        # Criar arquivo de teste no workspace
        test_file_path = os.path.join(self.test_dir, "hello.txt")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write("Hello MCP World!")

        # Testar listar_arquivos
        listing = mcp.listar_arquivos()
        self.assertIn("hello.txt", listing)

        # Testar ler_arquivo
        content = mcp.ler_arquivo("hello.txt")
        self.assertEqual(content, "Hello MCP World!")

        # Testar leitura fora do workspace (Path Traversal block)
        outside_read = mcp.ler_arquivo("../outside.txt")
        self.assertIn("Erro de segurança", outside_read)

        # Testar executar_comando seguro
        cmd_res = mcp.executar_comando("echo 'MCP Test'")
        self.assertIn("MCP Test", cmd_res)

        # Testar comando perigoso sem confirmação
        danger_res = mcp.executar_comando("rm -rf test")
        self.assertIn("ALERTA DE SEGURANÇA", danger_res)
        self.assertIn("CONFIRMATION_REQUIRED", danger_res)

        # Testar comando perigoso com confirmação explícita
        confirmed_res = mcp.executar_comando("rm -rf test", confirmed=True)
        # Como o diretório 'test' não existe, deve rodar sem erro fatal
        self.assertIsInstance(confirmed_res, str)

if __name__ == "__main__":
    unittest.main()

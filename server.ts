import express from 'express';
import cors from 'cors';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { GoogleGenAI, Type, FunctionDeclaration } from '@google/genai';
import { exec } from 'child_process';
import util from 'util';

const execPromise = util.promisify(exec);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function startServer() {
  const app = express();
  const PORT = Number(process.env.PORT) || 3000;

  app.use(cors());
  app.use(express.json());

  // TuxAssist Configuration & Workspace Directory handling
  const CONFIG_FILE = path.resolve(__dirname, 'tuxassist_config.json');

  function loadTuxConfig(): Record<string, any> {
    try {
      if (fs.existsSync(CONFIG_FILE)) {
        const data = fs.readFileSync(CONFIG_FILE, 'utf-8');
        return JSON.parse(data);
      }
    } catch (e) {
      console.error('Erro ao ler tuxassist_config.json:', e);
    }
    return {};
  }

  function saveTuxConfig(newConfig: Record<string, any>) {
    try {
      const existing = loadTuxConfig();
      const merged = { ...existing, ...newConfig };
      fs.writeFileSync(CONFIG_FILE, JSON.stringify(merged, null, 2), 'utf-8');
      return merged;
    } catch (e) {
      console.error('Erro ao salvar tuxassist_config.json:', e);
      throw e;
    }
  }

  let activeWorkspaceDir = process.cwd();

  const initialConfig = loadTuxConfig();
  if (initialConfig.workspace_dir) {
    let target = String(initialConfig.workspace_dir).trim();
    if (target.startsWith('~')) {
      target = path.join(process.env.HOME || process.env.USERPROFILE || '/', target.slice(1));
    }
    const resolved = path.resolve(target);
    try {
      if (fs.existsSync(resolved) && fs.statSync(resolved).isDirectory()) {
        fs.readdirSync(resolved);
        activeWorkspaceDir = resolved;
        console.log(`📂 Workspace ativo carregado: ${activeWorkspaceDir}`);
      } else {
        console.warn(`⚠️ workspace_dir configurado (${resolved}) é inválido ou não existe. Usando fallback: ${activeWorkspaceDir}`);
      }
    } catch (e) {
      console.warn(`⚠️ Sem permissão para acessar workspace_dir configurado (${resolved}): ${e}. Usando fallback: ${activeWorkspaceDir}`);
    }
  }

  // MCP Tools definitions for AI agents
  const mcpToolsDeclarations: FunctionDeclaration[] = [
    {
      name: "listar_arquivos",
      description: "Lista todos os arquivos de um diretório e vasculha DENTRO de todas as subpastas automaticamente.",
      parameters: {
        type: Type.OBJECT,
        properties: {
          pasta: { type: Type.STRING, description: "Caminho da pasta (padrão '.')" }
        }
      }
    },
    {
      name: "ler_arquivo",
      description: "Lê e retorna o conteúdo de um arquivo de texto no workspace.",
      parameters: {
        type: Type.OBJECT,
        properties: {
          arquivo: { type: Type.STRING, description: "Caminho do arquivo" }
        },
        required: ["arquivo"]
      }
    },
    {
      name: "executar_comando",
      description: "Executa um comando no terminal do sistema e retorna a saída.",
      parameters: {
        type: Type.OBJECT,
        properties: {
          comando: { type: Type.STRING, description: "Comando de terminal a executar" }
        },
        required: ["comando"]
      }
    },
    {
      name: "comando_remoto_esp32",
      description: "Acessa o ESP32-S3 via rede local (Socket TCP) e executa um comando nele.",
      parameters: {
        type: Type.OBJECT,
        properties: {
          comando: { type: Type.STRING, description: "Comando para o ESP32" }
        },
        required: ["comando"]
      }
    }
  ];

  // Security classification for commands
  function classifyCommand(cmd: string): { riskLevel: number; reason: string } {
    const trimmed = (cmd || "").trim().toLowerCase();
    if (
      trimmed.startsWith('rm ') || 
      trimmed.includes(' rm ') || 
      trimmed.startsWith('sudo') || 
      trimmed.startsWith('su') || 
      trimmed.includes('python3 -c') || 
      trimmed.includes('python -c') || 
      trimmed.includes('eval') || 
      trimmed.includes('bash -c') || 
      trimmed.includes('sh -c') || 
      trimmed.includes('dd if=') || 
      trimmed.includes('mkfs') || 
      trimmed.startsWith('chmod 777') || 
      trimmed.startsWith('chown')
    ) {
      return { riskLevel: 2, reason: 'Comando potencialmente perigoso ou de execução direta no sistema (ex: exclusão, sudo, python -c).' };
    }
    if (
      trimmed.startsWith('apt') || 
      trimmed.startsWith('pip') || 
      trimmed.startsWith('npm install') || 
      trimmed.startsWith('wget') || 
      trimmed.startsWith('curl') || 
      trimmed.startsWith('kill')
    ) {
      return { riskLevel: 1, reason: 'Comando de modificação de sistema ou download de rede.' };
    }
    return { riskLevel: 0, reason: 'Comando seguro de leitura ou navegação.' };
  }

  // Path traversal security validation (relative_to and resolve verification)
  function isPathSafe(targetPath: string, baseDir: string): boolean {
    try {
      const resolvedBase = path.resolve(baseDir);
      const resolvedTarget = path.resolve(resolvedBase, targetPath);
      const rel = path.relative(resolvedBase, resolvedTarget);
      if (rel.startsWith('..') && path.isAbsolute(rel)) return false;
      const segments = rel.split(path.sep);
      if (segments.includes('..')) return false;
      return resolvedTarget === resolvedBase || resolvedTarget.startsWith(resolvedBase + path.sep);
    } catch {
      return false;
    }
  }

  // Tool execution handler implementation
  async function executeMcpTool(name: string, args: Record<string, any> | undefined = {}): Promise<string> {
    const safeArgs = args || {};
    try {
      if (name === "listar_arquivos") {
        const pasta = safeArgs.pasta || ".";
        const resultado: string[] = [];
        const targetDir = path.resolve(activeWorkspaceDir, pasta);
        
        if (!isPathSafe(targetDir, activeWorkspaceDir)) {
          return `Erro de segurança: Acesso negado. O caminho '${pasta}' está fora do diretório autorizado (${activeWorkspaceDir}).`;
        }

        const walk = (dir: string, base: string = "") => {
          if (resultado.length >= 300) return;
          if (!fs.existsSync(dir)) return;
          const entries = fs.readdirSync(dir, { withFileTypes: true });
          for (const entry of entries) {
            if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === '__pycache__') continue;
            const relPath = base ? path.join(base, entry.name) : entry.name;
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
              walk(fullPath, relPath);
            } else {
              resultado.push(relPath);
              if (resultado.length >= 300) break;
            }
          }
        };

        if (fs.existsSync(targetDir)) {
          walk(targetDir);
        } else {
          return `Diretório não encontrado: ${pasta}`;
        }

        if (resultado.length === 0) return "A pasta está vazia.";
        let texto = resultado.join("\n");
        if (resultado.length >= 300) {
          texto += "\n\n[...lista cortada em 300 arquivos...]";
        }
        return texto;
      }

      if (name === "ler_arquivo") {
        const arquivo = safeArgs.arquivo;
        if (!arquivo) return "Erro: arquivo não especificado.";
        const fullPath = path.resolve(activeWorkspaceDir, arquivo);
        if (!isPathSafe(fullPath, activeWorkspaceDir)) {
          return `Erro de segurança: Acesso negado. O arquivo '${arquivo}' está fora do diretório autorizado (${activeWorkspaceDir}).`;
        }
        if (fs.existsSync(fullPath)) {
          return fs.readFileSync(fullPath, 'utf-8');
        }
        return `Arquivo não encontrado: ${arquivo}`;
      }

      if (name === "executar_comando") {
        const comando = safeArgs.comando;
        const confirmed = safeArgs.confirmed === true;
        if (!comando) return "Erro: comando não especificado.";

        const sec = classifyCommand(comando);
        if (sec.riskLevel >= 2 && !confirmed) {
          return `⚠️ ALERTA DE SEGURANÇA (Nível 2): O comando abaixo requer sua autorização:\n${comando}\n\n[CONFIRMATION_REQUIRED:2:${encodeURIComponent(comando)}:${encodeURIComponent(sec.reason)}]`;
        }

        try {
          const { stdout, stderr } = await execPromise(comando, { cwd: activeWorkspaceDir, timeout: 15000 });
          const saida = (stdout || "") + (stderr || "");
          return saida.trim() ? saida : "Comando executado com sucesso (sem saída de texto).";
        } catch (err: any) {
          return `Erro ao executar comando: ${err.message || err}`;
        }
      }

      if (name === "comando_remoto_esp32") {
        return `[Simulação ESP32] Comando enviado com sucesso para 192.168.0.100:2222 -> "${safeArgs.comando}". Resposta: OK (Modo Web Sandbox)`;
      }

      return `Ferramenta desconhecida: ${name}`;
    } catch (e: any) {
      return `Erro na execução da ferramenta ${name}: ${e.message || e}`;
    }
  }

  // API Endpoints
  app.get('/api/tools', (req, res) => {
    res.json({ tools: mcpToolsDeclarations });
  });

  app.get('/api/config', (req, res) => {
    res.json({
      config: loadTuxConfig(),
      activeWorkspaceDir
    });
  });

  app.post('/api/config/home', (req, res) => {
    try {
      let { workspace_dir } = req.body;
      if (!workspace_dir || typeof workspace_dir !== 'string') {
        return res.status(400).json({ error: 'Diretório não especificado.' });
      }

      let target = workspace_dir.trim();
      if (target.startsWith('~')) {
        target = path.join(process.env.HOME || process.env.USERPROFILE || '/', target.slice(1));
      }
      const resolved = path.resolve(target);

      // 4. Verificar se o diretório existe
      if (!fs.existsSync(resolved)) {
        return res.status(400).json({
          success: false,
          error: `✗ Diretório inválido.\n\nA pasta informada não existe (${resolved}).\nA configuração anterior foi preservada.`
        });
      }

      // 5. Verificar se realmente é um diretório
      const stats = fs.statSync(resolved);
      if (!stats.isDirectory()) {
        return res.status(400).json({
          success: false,
          error: `✗ Diretório inválido.\n\nO caminho informado não é um diretório (${resolved}).\nA configuração anterior foi preservada.`
        });
      }

      // 6. Verificar se o processo tem permissão para acessá-lo
      try {
        fs.readdirSync(resolved);
      } catch (permErr) {
        return res.status(403).json({
          success: false,
          error: `✗ Diretório inválido.\n\nSem permissão para acessar o diretório (${resolved}).\nA configuração anterior foi preservada.`
        });
      }

      // 7. Salvar a configuração permanentemente em tuxassist_config.json
      saveTuxConfig({ workspace_dir: resolved });

      // 8. Atualizar imediatamente a pasta de trabalho
      activeWorkspaceDir = resolved;

      // 9. Mostrar mensagem de sucesso
      const successMsg = `✓ Diretório padrão atualizado!\n\n${resolved}\n\nAs próximas operações utilizarão esse diretório.`;
      res.json({ success: true, message: successMsg, activeWorkspaceDir: resolved });
    } catch (e: any) {
      res.status(500).json({ success: false, error: `Erro ao configurar diretório: ${e.message || e}` });
    }
  });

  app.get('/api/files', (req, res) => {
    try {
      const files: { name: string; path: string; isDir: boolean }[] = [];
      const walk = (dir: string, base: string = "") => {
        if (!fs.existsSync(dir)) return;
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === '__pycache__' || entry.name === 'dist') continue;
          const relPath = base ? path.join(base, entry.name) : entry.name;
          files.push({ name: entry.name, path: relPath, isDir: entry.isDirectory() });
        }
      };
      walk(activeWorkspaceDir);
      res.json({ files });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/files/read', (req, res) => {
    try {
      const { filepath } = req.body;
      if (!filepath) return res.status(400).json({ error: 'filepath required' });
      const fullPath = path.resolve(activeWorkspaceDir, filepath);
      if (!isPathSafe(fullPath, activeWorkspaceDir)) {
        return res.status(403).json({ error: 'Acesso negado fora do diretório autorizado.' });
      }
      if (fs.existsSync(fullPath) && fs.statSync(fullPath).isFile()) {
        const content = fs.readFileSync(fullPath, 'utf-8');
        res.json({ content });
      } else {
        res.status(404).json({ error: 'File not found' });
      }
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/execute', async (req, res) => {
    try {
      const { command, confirmed } = req.body;
      if (!command) return res.status(400).json({ error: 'command required' });

      const sec = classifyCommand(command);
      if (sec.riskLevel >= 2 && !confirmed) {
        return res.status(403).json({ 
          requiresConfirmation: true, 
          riskLevel: sec.riskLevel, 
          reason: sec.reason,
          command 
        });
      }

      const { stdout, stderr } = await execPromise(command, { cwd: activeWorkspaceDir, timeout: 15000 });
      res.json({ output: (stdout || "") + (stderr || "") });
    } catch (e: any) {
      res.status(500).json({ output: `Erro: ${e.message || e}` });
    }
  });

  // Chat API supporting Gemini, Groq, and OpenAI
  app.post('/api/chat', async (req, res) => {
    try {
      const { provider, apiKey, model, messages } = req.body;
      const key = apiKey || process.env.GEMINI_API_KEY || process.env.GROQ_API_KEY || process.env.OPENAI_API_KEY;

      if (!key && provider === 'gemini') {
        return res.status(400).json({ error: 'API Key do Gemini não fornecida.' });
      }

      const systemInstruction = "Você é o TuxAssist, um assistente inteligente com acesso a ferramentas MCP para listar arquivos, ler códigos e executar comandos no terminal. Responda de forma prestativa, técnica e direta em português.";

      if (provider === 'gemini') {
        const ai = new GoogleGenAI({ apiKey: key || '' });
        const geminiModel = model || 'gemini-2.5-flash';

        // Format history for Gemini chat
        const chatHistory = messages.slice(0, -1).map((m: any) => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: m.content }]
        }));

        const chat = ai.chats.create({
          model: geminiModel,
          config: {
            systemInstruction,
            tools: [{ functionDeclarations: mcpToolsDeclarations }]
          },
          history: chatHistory
        });

        const lastMessage = messages[messages.length - 1].content;
        let response = await chat.sendMessage(lastMessage);

        const executionSteps: any[] = [];

        // Handle tool calls in a loop
        while (response.functionCalls && response.functionCalls.length > 0) {
          const functionResponses = [];
          for (const fc of response.functionCalls) {
            const toolName = fc.name || '';
            const toolResult = await executeMcpTool(toolName, fc.args as any);
            executionSteps.push({
              tool: toolName,
              args: fc.args,
              result: toolResult
            });
            functionResponses.push({
              functionResponse: {
                name: fc.name,
                response: { result: toolResult.length > 4000 ? toolResult.slice(0, 4000) + "\n[cortado]" : toolResult }
              }
            });
          }
          response = await chat.sendMessage(functionResponses as any);
        }

        return res.json({
          reply: response.text || "Sem resposta do modelo.",
          steps: executionSteps
        });
      } else {
        // Groq or OpenAI via direct REST call
        const url = provider === 'groq' 
          ? 'https://api.groq.com/openai/v1/chat/completions' 
          : 'https://api.openai.com/v1/chat/completions';

        const openaiTools = mcpToolsDeclarations.map(t => ({
          type: 'function',
          function: {
            name: t.name,
            description: t.description,
            parameters: t.parameters
          }
        }));

        const formattedMessages = [
          { role: 'system', content: systemInstruction },
          ...messages.map((m: any) => ({ role: m.role, content: m.content }))
        ];

        const payload: any = {
          model: model || (provider === 'groq' ? 'llama-3.3-70b-versatile' : 'gpt-4o'),
          messages: formattedMessages,
          tools: openaiTools,
          tool_choice: 'auto'
        };

        const fetchResponse = await fetch(url, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${key}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        if (!fetchResponse.ok) {
          const errText = await fetchResponse.text();
          return res.status(fetchResponse.status).json({ error: `Erro na API ${provider}: ${errText}` });
        }

        const data = await fetchResponse.json();
        let msg = data.choices[0].message;
        const executionSteps: any[] = [];

        while (msg.tool_calls) {
          formattedMessages.push(msg);
          for (const tc of msg.tool_calls) {
            const fName = tc.function.name;
            const fArgs = JSON.parse(tc.function.arguments || '{}');
            const toolResult = await executeMcpTool(fName, fArgs);

            executionSteps.push({
              tool: fName,
              args: fArgs,
              result: toolResult
            });

            formattedMessages.push({
              role: 'tool',
              tool_call_id: tc.id,
              name: fName,
              content: toolResult.length > 4000 ? toolResult.slice(0, 4000) + "\n[cortado]" : toolResult
            });
          }

          const followUpPayload = {
            model: payload.model,
            messages: formattedMessages,
            tools: openaiTools,
            tool_choice: 'auto'
          };

          const followUpRes = await fetch(url, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${key}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(followUpPayload)
          });

          if (!followUpRes.ok) break;
          const followUpData = await followUpRes.json();
          msg = followUpData.choices[0].message;
        }

        return res.json({
          reply: msg.content || "Sem resposta.",
          steps: executionSteps
        });
      }
    } catch (e: any) {
      console.error(e);
      res.status(500).json({ error: e.message || String(e) });
    }
  });

  // Vite middleware in development
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true, hmr: false },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 TuxAssist Web running on http://0.0.0.0:${PORT}`);
  });
}

startServer();

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

  // Tool execution handler implementation
  async function executeMcpTool(name: string, args: Record<string, any> | undefined = {}): Promise<string> {
    const safeArgs = args || {};
    try {
      if (name === "listar_arquivos") {
        const pasta = safeArgs.pasta || ".";
        const resultado: string[] = [];
        const targetDir = path.resolve(process.cwd(), pasta);
        
        const walk = (dir: string, base: string = "") => {
          if (resultado.length >= 300) return;
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
        const arquivo = args.arquivo;
        if (!arquivo) return "Erro: arquivo não especificado.";
        const fullPath = path.resolve(process.cwd(), arquivo);
        if (fs.existsSync(fullPath)) {
          return fs.readFileSync(fullPath, 'utf-8');
        }
        return `Arquivo não encontrado: ${arquivo}`;
      }

      if (name === "executar_comando") {
        const comando = args.comando;
        if (!comando) return "Erro: comando não especificado.";
        try {
          const { stdout, stderr } = await execPromise(comando, { timeout: 15000 });
          const saida = (stdout || "") + (stderr || "");
          return saida.trim() ? saida : "Comando executado com sucesso (sem saída de texto).";
        } catch (err: any) {
          return `Erro ao executar comando: ${err.message || err}`;
        }
      }

      if (name === "comando_remoto_esp32") {
        return `[Simulação ESP32] Comando enviado com sucesso para 192.168.0.100:2222 -> "${args.comando}". Resposta: OK (Modo Web Sandbox)`;
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

  app.get('/api/files', (req, res) => {
    try {
      const files: { name: string; path: string; isDir: boolean }[] = [];
      const walk = (dir: string, base: string = "") => {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
          if (entry.name.startsWith('.') || entry.name === 'node_modules' || entry.name === '__pycache__' || entry.name === 'dist') continue;
          const relPath = base ? path.join(base, entry.name) : entry.name;
          files.push({ name: entry.name, path: relPath, isDir: entry.isDirectory() });
        }
      };
      walk(process.cwd());
      res.json({ files });
    } catch (e: any) {
      res.status(500).json({ error: e.message });
    }
  });

  app.post('/api/files/read', (req, res) => {
    try {
      const { filepath } = req.body;
      if (!filepath) return res.status(400).json({ error: 'filepath required' });
      const fullPath = path.resolve(process.cwd(), filepath);
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
      const { command } = req.body;
      if (!command) return res.status(400).json({ error: 'command required' });
      const { stdout, stderr } = await execPromise(command, { timeout: 15000 });
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

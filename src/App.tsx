import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal, FolderOpen, FileText, Cpu, Settings, Send, RefreshCw, 
  Trash2, Play, CheckCircle2, AlertCircle, Wrench, Sparkles, 
  Code, Key, Layers, ShieldAlert, ChevronRight, Eye
} from 'lucide-react';

interface Message {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  steps?: { tool: string; args: any; result: string }[];
}

interface FileItem {
  name: string;
  path: string;
  isDir: boolean;
}

interface McpTool {
  name: string;
  description: string;
  parameters: any;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'files' | 'terminal' | 'tools' | 'settings'>('chat');
  
  // Settings State
  const [provider, setProvider] = useState<string>(() => localStorage.getItem('tux_provider') || 'gemini');
  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem('tux_apikey') || '');
  const [model, setModel] = useState<string>(() => localStorage.getItem('tux_model') || 'gemini-2.5-flash');

  // Chat State
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: '🤖 **Bem-vindo ao TuxAssist Web!** Sou seu agente de IA integrado ao Protocolo MCP (Model Context Protocol). Posso listar arquivos, ler códigos, executar comandos no terminal e interagir com o ambiente. Como posso ajudar hoje?'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Files State
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string>('');
  const [loadingFiles, setLoadingFiles] = useState(false);

  // Terminal State
  const [termCommand, setTermCommand] = useState('');
  const [termHistory, setTermHistory] = useState<{ cmd: string; output: string }[]>([
    { cmd: 'uname -a', output: 'Linux ais-applet-container 6.5.0-generic x86_64 GNU/Linux' },
    { cmd: 'python --version', output: 'Python 3.11.8' }
  ]);
  const [termRunning, setTermRunning] = useState(false);

  // MCP Tools State
  const [mcpTools, setMcpTools] = useState<McpTool[]>([]);
  const [selectedTool, setSelectedTool] = useState<string>('');
  const [toolArgs, setToolArgs] = useState<string>('{}');
  const [toolResult, setToolResult] = useState<string>('');
  const [testingTool, setTestingTool] = useState(false);

  // Home Workspace State
  const [homeModalOpen, setHomeModalOpen] = useState(false);
  const [currentWorkspaceDir, setCurrentWorkspaceDir] = useState('');
  const [newWorkspaceDirInput, setNewWorkspaceDirInput] = useState('');
  const [homeResultMsg, setHomeResultMsg] = useState('');
  const [homeResultError, setHomeResultError] = useState('');
  const [loadingConfig, setLoadingConfig] = useState(false);

  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      if (data.activeWorkspaceDir) {
        setCurrentWorkspaceDir(data.activeWorkspaceDir);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveWorkspaceHome = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newWorkspaceDirInput.trim()) return;

    setHomeResultMsg('');
    setHomeResultError('');
    setLoadingConfig(true);

    try {
      const res = await fetch('/api/config/home', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace_dir: newWorkspaceDirInput.trim() })
      });
      const data = await res.json();

      if (res.ok && data.success) {
        setCurrentWorkspaceDir(data.activeWorkspaceDir);
        setHomeResultMsg(data.message);
        fetchFiles();
        setTimeout(() => {
          setHomeModalOpen(false);
        }, 3000);
      } else {
        setHomeResultError(data.error || 'Erro ao atualizar diretório.');
      }
    } catch (e: any) {
      setHomeResultError(`Erro de conexão: ${e.message}`);
    } finally {
      setLoadingConfig(false);
    }
  };

  // Security Confirmation Modal State
  const [pendingConfirmation, setPendingConfirmation] = useState<{
    command: string;
    riskLevel: number;
    reason: string;
    source: 'terminal' | 'tool' | 'chat';
    callback: (confirmed: boolean) => void;
  } | null>(null);
  const [confirmInput, setConfirmInput] = useState('');
  const [confirmError, setConfirmError] = useState('');

  const handleConfirmChoice = (choice: string) => {
    const clean = choice.trim().toLowerCase();
    if (['y', 'yes', 's', 'sim'].includes(clean)) {
      setConfirmError('');
      const cb = pendingConfirmation?.callback;
      setPendingConfirmation(null);
      setConfirmInput('');
      if (cb) cb(true);
    } else if (['n', 'no', 'não', 'nao'].includes(clean)) {
      setConfirmError('');
      const cb = pendingConfirmation?.callback;
      setPendingConfirmation(null);
      setConfirmInput('');
      if (cb) cb(false);
    } else {
      setConfirmError('Entrada inválida. Digite y, s ou sim para autorizar, ou n, não para cancelar.');
    }
  };

  useEffect(() => {
    if (messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];
    if (lastMsg.steps && lastMsg.steps.length > 0) {
      for (const step of lastMsg.steps) {
        if (step.result && step.result.includes('[CONFIRMATION_REQUIRED')) {
          const match = step.result.match(/\[CONFIRMATION_REQUIRED:(\d+):(.*?):(.*?)]/);
          if (match) {
            const riskLevel = parseInt(match[1], 10);
            const cmd = decodeURIComponent(match[2]);
            const reason = decodeURIComponent(match[3]);
            
            if (!pendingConfirmation || pendingConfirmation.command !== cmd) {
              setPendingConfirmation({
                command: cmd,
                riskLevel,
                reason,
                source: 'chat',
                callback: async (isConfirmed) => {
                  if (isConfirmed) {
                    setInputMessage(`Executar comando confirmado: ${cmd}`);
                  } else {
                    setMessages(prev => [...prev, {
                      role: 'assistant',
                      content: `❌ Operação cancelada pelo usuário para o comando: \`${cmd}\``
                    }]);
                  }
                }
              });
            }
          }
        }
      }
    }
  }, [messages]);

  useEffect(() => {
    localStorage.setItem('tux_provider', provider);
    localStorage.setItem('tux_apikey', apiKey);
    localStorage.setItem('tux_model', model);
  }, [provider, apiKey, model]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  useEffect(() => {
    fetchFiles();
    fetchTools();
    fetchConfig();
  }, []);

  const fetchFiles = async () => {
    setLoadingFiles(true);
    try {
      const res = await fetch('/api/files');
      const data = await res.json();
      if (data.files) setFiles(data.files);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingFiles(false);
    }
  };

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/tools');
      const data = await res.json();
      if (data.tools) {
        setMcpTools(data.tools);
        if (data.tools.length > 0 && !selectedTool) {
          setSelectedTool(data.tools[0].name);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim() || isThinking) return;

    const userText = inputMessage.trim();
    if (userText === '/home' || userText.toLowerCase() === '/home') {
      setInputMessage('');
      fetchConfig();
      setNewWorkspaceDirInput(currentWorkspaceDir);
      setHomeResultMsg('');
      setHomeResultError('');
      setHomeModalOpen(true);
      return;
    }

    setInputMessage('');
    const newMessages: Message[] = [...messages, { role: 'user', content: userText }];
    setMessages(newMessages);
    setIsThinking(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          apiKey,
          model,
          messages: newMessages.map(m => ({ role: m.role, content: m.content }))
        })
      });

      const data = await res.json();
      if (data.error) {
        setMessages([...newMessages, { role: 'assistant', content: `❌ **Erro:** ${data.error}` }]);
      } else {
        setMessages([...newMessages, { 
          role: 'assistant', 
          content: data.reply,
          steps: data.steps 
        }]);
      }
    } catch (err: any) {
      setMessages([...newMessages, { role: 'assistant', content: `❌ **Erro de conexão:** ${err.message || err}` }]);
    } finally {
      setIsThinking(false);
    }
  };

  const loadFileContent = async (filepath: string) => {
    setSelectedFile(filepath);
    try {
      const res = await fetch('/api/files/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath })
      });
      const data = await res.json();
      if (data.content !== undefined) {
        setFileContent(data.content);
      } else {
        setFileContent(data.error || 'Erro ao ler arquivo.');
      }
    } catch (e: any) {
      setFileContent(`Erro: ${e.message}`);
    }
  };

  const runTerminalCommand = async (cmdToRun?: string) => {
    const cmd = cmdToRun || termCommand;
    if (!cmd.trim() || termRunning) return;
    if (!cmdToRun) setTermCommand('');
    executeCmdWithCheck(cmd, false, 'terminal');
  };

  const executeCmdWithCheck = async (cmd: string, confirmed: boolean, source: 'terminal' | 'tool' | 'chat') => {
    if (source === 'terminal') setTermRunning(true);
    if (source === 'tool') setTestingTool(true);
    try {
      const res = await fetch('/api/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: cmd, confirmed })
      });
      const data = await res.json();
      
      if (res.status === 403 && data.requiresConfirmation) {
        setPendingConfirmation({
          command: data.command,
          riskLevel: data.riskLevel,
          reason: data.reason,
          source,
          callback: (isConfirmed) => {
            if (isConfirmed) {
              executeCmdWithCheck(cmd, true, source);
            } else {
              if (source === 'terminal') {
                setTermHistory(prev => [...prev, { cmd, output: '❌ Operação cancelada pelo usuário (recusada).' }]);
              } else if (source === 'tool') {
                setToolResult('❌ Operação cancelada pelo usuário (recusada).');
              }
            }
          }
        });
        if (source === 'terminal') setTermRunning(false);
        if (source === 'tool') setTestingTool(false);
        return;
      }

      if (source === 'terminal') {
        setTermHistory(prev => [...prev, { cmd, output: data.output || data.error || '(sem saída)' }]);
      } else if (source === 'tool') {
        setToolResult(data.output || data.error || '(sem saída)');
      }
    } catch (e: any) {
      const errOut = `Erro: ${e.message}`;
      if (source === 'terminal') {
        setTermHistory(prev => [...prev, { cmd, output: errOut }]);
      } else if (source === 'tool') {
        setToolResult(errOut);
      }
    } finally {
      if (source === 'terminal') setTermRunning(false);
      if (source === 'tool') setTestingTool(false);
    }
  };

  const testMcpTool = async () => {
    setTestingTool(true);
    setToolResult('Executando ferramenta MCP...');
    try {
      let parsedArgs = {};
      try {
        parsedArgs = JSON.parse(toolArgs);
      } catch {
        setToolResult('Erro: Argumentos JSON inválidos.');
        setTestingTool(false);
        return;
      }

      let res;
      if (selectedTool === 'listar_arquivos') {
        res = await fetch('/api/files');
        const data = await res.json();
        setToolResult(JSON.stringify(data.files, null, 2));
        setTestingTool(false);
      } else if (selectedTool === 'ler_arquivo') {
        res = await fetch('/api/files/read', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsedArgs)
        });
        const data = await res.json();
        setToolResult(data.content || data.error || 'Erro');
        setTestingTool(false);
      } else if (selectedTool === 'executar_comando') {
        const cmd = (parsedArgs as any).comando;
        if (!cmd) {
          setToolResult('Erro: comando não especificado.');
          setTestingTool(false);
          return;
        }
        executeCmdWithCheck(cmd, false, 'tool');
      } else {
        res = await fetch('/api/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: `echo "[ESP32] Executando comando remoto: ${(parsedArgs as any).comando || ''}"` })
        });
        const data = await res.json();
        setToolResult(data.output);
        setTestingTool(false);
      }
    } catch (e: any) {
      setToolResult(`Erro: ${e.message}`);
      setTestingTool(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      
      {/* Sidebar */}
      <div className="w-64 bg-zinc-900 border-r border-zinc-800 flex flex-col justify-between">
        <div>
          {/* Logo / Header */}
          <div className="p-4 border-b border-zinc-800 flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-[#d97757]/20 flex items-center justify-center text-[#d97757] font-bold text-lg shadow-md shadow-[#d97757]/10">
              ✻
            </div>
            <div>
              <h1 className="font-bold text-zinc-100 tracking-wide text-sm">TuxAssist</h1>
              <p className="text-xs text-zinc-400">MCP AI Agent v1.0</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="p-3 space-y-1">
            <button
              onClick={() => setActiveTab('chat')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'chat' 
                  ? 'bg-[#d97757] text-white shadow-lg shadow-[#d97757]/20' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <Cpu className="w-4 h-4" />
              <span>Chat & Agente</span>
            </button>

            <button
              onClick={() => setActiveTab('files')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'files' 
                  ? 'bg-[#d97757] text-white shadow-lg shadow-[#d97757]/20' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              <span>Arquivos do Projeto</span>
            </button>

            <button
              onClick={() => setActiveTab('terminal')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'terminal' 
                  ? 'bg-[#d97757] text-white shadow-lg shadow-[#d97757]/20' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <Terminal className="w-4 h-4" />
              <span>Terminal & Shell</span>
            </button>

            <button
              onClick={() => setActiveTab('tools')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'tools' 
                  ? 'bg-[#d97757] text-white shadow-lg shadow-[#d97757]/20' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <Wrench className="w-4 h-4" />
              <span>Ferramentas MCP</span>
            </button>

            <button
              onClick={() => {
                fetchConfig();
                setNewWorkspaceDirInput(currentWorkspaceDir);
                setHomeResultMsg('');
                setHomeResultError('');
                setHomeModalOpen(true);
              }}
              className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 transition-colors"
            >
              <FolderOpen className="w-4 h-4 text-amber-500" />
              <span>Configurar /home</span>
            </button>

            <button
              onClick={() => setActiveTab('settings')}
              className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'settings' 
                  ? 'bg-[#d97757] text-white shadow-lg shadow-[#d97757]/20' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
              }`}
            >
              <Settings className="w-4 h-4" />
              <span>Configurações & IA</span>
            </button>
          </nav>
        </div>

        {/* Footer info */}
        <div className="p-4 border-t border-zinc-800 text-xs text-zinc-500 space-y-1">
          <div className="flex justify-between items-center">
            <span className="capitalize font-medium text-zinc-400">Provedor:</span>
            <span className="text-[#d97757] font-bold">{provider}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="font-medium text-zinc-400">Modelo:</span>
            <span className="truncate max-w-[110px]" title={model}>{model}</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col bg-zinc-950 overflow-hidden">
        
        {/* Top Header */}
        <header className="h-14 border-b border-zinc-800 bg-zinc-900/50 backdrop-blur px-6 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-sm">
            <span className="text-zinc-400">Modo atual:</span>
            <span className="font-semibold text-zinc-200 capitalize flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              {activeTab === 'chat' && 'Assistente Inteligente MCP'}
              {activeTab === 'files' && 'Explorador de Arquivos'}
              {activeTab === 'terminal' && 'Terminal Interativo'}
              {activeTab === 'tools' && 'Inspetor de Ferramentas MCP'}
              {activeTab === 'settings' && 'Configurações de Provedor de IA'}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <div className="text-xs bg-zinc-900 border border-zinc-800 px-3 py-1.5 rounded-md text-zinc-400 font-mono flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-[#d97757]" />
              <span>MCP Server Ativo</span>
            </div>
          </div>
        </header>

        {/* Tab 1: Chat */}
        {activeTab === 'chat' && (
          <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)]">
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-3xl rounded-2xl p-4 shadow-sm ${
                    msg.role === 'user' 
                      ? 'bg-[#d97757] text-white rounded-br-none' 
                      : 'bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-bl-none'
                  }`}>
                    {/* Tool Steps executed */}
                    {msg.steps && msg.steps.length > 0 && (
                      <div className="mb-3 space-y-2 border-b border-zinc-800 pb-3">
                        <div className="text-xs font-semibold text-[#d97757] flex items-center gap-1.5">
                          <Wrench className="w-3.5 h-3.5" />
                          <span>Ferramentas MCP Executadas pela IA:</span>
                        </div>
                        {msg.steps.map((step, sIdx) => (
                          <div key={sIdx} className="bg-zinc-950/70 border border-zinc-800/80 rounded p-2 text-xs font-mono space-y-1">
                            <div className="text-zinc-300 font-bold flex items-center gap-1">
                              <span className="text-[#d97757]">●</span> {step.tool}({JSON.stringify(step.args)})
                            </div>
                            <div className="text-zinc-500 max-h-24 overflow-y-auto whitespace-pre-wrap">
                              {step.result}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="whitespace-pre-wrap leading-relaxed text-sm">
                      {msg.content}
                    </div>
                  </div>
                </div>
              ))}

              {isThinking && (
                <div className="flex justify-start">
                  <div className="bg-zinc-900 border border-zinc-800 text-zinc-400 rounded-2xl rounded-bl-none p-4 flex items-center space-x-3 text-sm">
                    <RefreshCw className="w-4 h-4 animate-spin text-[#d97757]" />
                    <span>TuxAssist está pensando e consultando ferramentas MCP...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <div className="p-4 bg-zinc-900/80 border-t border-zinc-800">
              <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-3">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ex: Liste os arquivos do projeto e leia o arquivo chat.py..."
                  className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-[#d97757] transition-colors"
                />
                <button
                  type="submit"
                  disabled={isThinking || !inputMessage.trim()}
                  className="bg-[#d97757] hover:bg-[#c26749] disabled:opacity-50 text-white px-5 py-3 rounded-xl font-medium text-sm flex items-center gap-2 transition-colors shadow-lg shadow-[#d97757]/20"
                >
                  <span>Enviar</span>
                  <Send className="w-4 h-4" />
                </button>
              </form>
              <div className="max-w-4xl mx-auto mt-2 flex items-center justify-between text-xs text-zinc-500 px-1">
                <span>Dica: Peça para a IA ler arquivos ou rodar testes.</span>
                <span>Provedor: {provider.toUpperCase()} ({model})</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Files */}
        {activeTab === 'files' && (
          <div className="flex-1 flex h-[calc(100vh-3.5rem)] overflow-hidden">
            {/* File Tree Sidebar */}
            <div className="w-80 border-r border-zinc-800 bg-zinc-900/30 flex flex-col">
              <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                  <FolderOpen className="w-4 h-4 text-[#d97757]" />
                  <span>Workspace Files</span>
                </h3>
                <button onClick={fetchFiles} className="p-1.5 text-zinc-400 hover:text-zinc-200 rounded hover:bg-zinc-800">
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingFiles ? 'animate-spin' : ''}`} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-2 space-y-1 font-mono text-xs">
                {files.map((file, idx) => (
                  <button
                    key={idx}
                    onClick={() => !file.isDir && loadFileContent(file.path)}
                    className={`w-full text-left px-3 py-2 rounded flex items-center space-x-2 transition-colors ${
                      selectedFile === file.path 
                        ? 'bg-[#d97757]/20 text-[#d97757] border border-[#d97757]/30' 
                        : 'text-zinc-300 hover:bg-zinc-800/60'
                    }`}
                  >
                    {file.isDir ? <FolderOpen className="w-3.5 h-3.5 text-amber-500" /> : <FileText className="w-3.5 h-3.5 text-blue-400" />}
                    <span className="truncate">{file.path}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* File Viewer */}
            <div className="flex-1 flex flex-col bg-zinc-950 overflow-hidden">
              <div className="p-4 border-b border-zinc-800 bg-zinc-900/50 flex items-center justify-between">
                <span className="font-mono text-xs text-zinc-400">
                  {selectedFile ? `Visualizando: ${selectedFile}` : 'Selecione um arquivo para ler'}
                </span>
              </div>
              <div className="flex-1 p-6 overflow-auto">
                {selectedFile ? (
                  <pre className="font-mono text-xs text-zinc-300 whitespace-pre-wrap bg-zinc-900/60 p-6 rounded-xl border border-zinc-800">
                    {fileContent}
                  </pre>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-zinc-500 space-y-2">
                    <FileText className="w-12 h-12 stroke-1 text-zinc-600" />
                    <p className="text-sm">Nenhum arquivo selecionado</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Terminal */}
        {activeTab === 'terminal' && (
          <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] bg-zinc-950 p-6">
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl flex-1 flex flex-col overflow-hidden shadow-xl">
              <div className="px-4 py-3 bg-zinc-900/80 border-b border-zinc-800 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                  <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                  <span className="ml-2 font-mono text-xs text-zinc-400">Terminal Shell (bash)</span>
                </div>
                <button 
                  onClick={() => setTermHistory([])}
                  className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1 bg-zinc-800 px-2.5 py-1 rounded"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>Limpar</span>
                </button>
              </div>

              <div className="flex-1 p-4 overflow-y-auto font-mono text-xs space-y-4">
                {termHistory.map((item, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="text-emerald-400 flex items-center gap-2">
                      <span>$</span>
                      <span className="font-bold text-zinc-200">{item.cmd}</span>
                    </div>
                    <pre className="text-zinc-300 whitespace-pre-wrap pl-4 border-l-2 border-zinc-800">
                      {item.output}
                    </pre>
                  </div>
                ))}
                {termRunning && (
                  <div className="text-amber-400 flex items-center gap-2">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Executando comando...</span>
                  </div>
                )}
              </div>

              <div className="p-3 bg-zinc-900/90 border-t border-zinc-800 flex items-center gap-2">
                <span className="text-emerald-400 font-mono font-bold pl-2">$</span>
                <input
                  type="text"
                  value={termCommand}
                  onChange={(e) => setTermCommand(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && runTerminalCommand()}
                  placeholder="Digite um comando (ex: ls -la, python --version)..."
                  className="flex-1 bg-transparent border-none text-zinc-100 font-mono text-xs focus:outline-none placeholder-zinc-600"
                />
                <button
                  onClick={() => runTerminalCommand()}
                  disabled={termRunning || !termCommand.trim()}
                  className="bg-[#d97757] hover:bg-[#c26749] text-white px-4 py-1.5 rounded font-medium text-xs flex items-center gap-1.5 transition-colors"
                >
                  <Play className="w-3 h-3" />
                  <span>Executar</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 4: Tools */}
        {activeTab === 'tools' && (
          <div className="flex-1 flex h-[calc(100vh-3.5rem)] overflow-hidden">
            <div className="w-80 border-r border-zinc-800 bg-zinc-900/30 flex flex-col p-4 space-y-3">
              <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Wrench className="w-4 h-4 text-[#d97757]" />
                <span>Ferramentas MCP Disponíveis</span>
              </h3>
              <div className="space-y-2">
                {mcpTools.map((tool, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setSelectedTool(tool.name);
                      if (tool.name === 'listar_arquivos') setToolArgs(JSON.stringify({ pasta: "." }, null, 2));
                      if (tool.name === 'ler_arquivo') setToolArgs(JSON.stringify({ arquivo: "README.md" }, null, 2));
                      if (tool.name === 'executar_comando') setToolArgs(JSON.stringify({ comando: "ls -la" }, null, 2));
                      if (tool.name === 'comando_remoto_esp32') setToolArgs(JSON.stringify({ comando: "status" }, null, 2));
                    }}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      selectedTool === tool.name 
                        ? 'bg-[#d97757]/10 border-[#d97757] text-zinc-100' 
                        : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <div className="font-mono text-xs font-bold text-[#d97757]">{tool.name}</div>
                    <div className="text-xs text-zinc-400 mt-1 line-clamp-2">{tool.description}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 flex flex-col p-6 overflow-y-auto space-y-6">
              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-bold text-zinc-100 font-mono text-[#d97757]">{selectedTool}</h2>
                    <p className="text-xs text-zinc-400 mt-1">
                      {mcpTools.find(t => t.name === selectedTool)?.description}
                    </p>
                  </div>
                  <button
                    onClick={testMcpTool}
                    disabled={testingTool}
                    className="bg-[#d97757] hover:bg-[#c26749] text-white px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 shadow-md"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Testar Ferramenta</span>
                  </button>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Argumentos (JSON):</label>
                  <textarea
                    rows={4}
                    value={toolArgs}
                    onChange={(e) => setToolArgs(e.target.value)}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-xs font-mono text-zinc-200 focus:outline-none focus:border-[#d97757]"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-medium text-zinc-400">Resultado da Execução:</label>
                  <pre className="w-full bg-zinc-950 border border-zinc-800 rounded-xl p-4 text-xs font-mono text-zinc-300 min-h-[150px] max-h-[300px] overflow-auto whitespace-pre-wrap">
                    {toolResult || 'Clique em "Testar Ferramenta" para executar.'}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 5: Settings */}
        {activeTab === 'settings' && (
          <div className="flex-1 flex flex-col p-8 overflow-y-auto max-w-3xl">
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-bold text-zinc-100">Configuração de IA & Provedores</h2>
                <p className="text-sm text-zinc-400 mt-1">Configure sua chave de API e selecione o provedor e modelo de Inteligência Artificial para o TuxAssist.</p>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-6">
                <div className="space-y-3">
                  <label className="text-sm font-medium text-zinc-300">Provedor de IA:</label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: 'gemini', name: 'Gemini (Google)', desc: 'Recomendado' },
                      { id: 'groq', name: 'Groq', desc: 'Ultra rápido' },
                      { id: 'openai', name: 'OpenAI', desc: 'ChatGPT' }
                    ].map((p) => (
                      <button
                        key={p.id}
                        onClick={() => {
                          setProvider(p.id);
                          if (p.id === 'gemini') setModel('gemini-2.5-flash');
                          if (p.id === 'groq') setModel('llama-3.3-70b-versatile');
                          if (p.id === 'openai') setModel('gpt-4o');
                        }}
                        className={`p-4 rounded-xl border text-left transition-all ${
                          provider === p.id 
                            ? 'bg-[#d97757]/10 border-[#d97757] text-zinc-100' 
                            : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200'
                        }`}
                      >
                        <div className="font-bold text-sm">{p.name}</div>
                        <div className="text-xs text-zinc-500 mt-1">{p.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">Modelo:</label>
                  <input
                    type="text"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    placeholder="Ex: gemini-2.5-flash, llama-3.3-70b-versatile, gpt-4o..."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-100 focus:outline-none focus:border-[#d97757]"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300 flex items-center justify-between">
                    <span>API Key ({provider.toUpperCase()}):</span>
                    <span className="text-xs text-zinc-500">Salvo localmente no navegador</span>
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder="Cole sua API Key aqui (ou use variável de ambiente no servidor)..."
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-100 focus:outline-none focus:border-[#d97757]"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Security Confirmation Modal */}
      {pendingConfirmation && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl animate-in fade-in zoom-in duration-200">
            <div className="flex items-center space-x-3 text-amber-500">
              <ShieldAlert className="w-6 h-6" />
              <h3 className="text-lg font-bold text-zinc-100">⚠️ CONFIRMAÇÃO DE SEGURANÇA</h3>
            </div>
            
            <div className="space-y-3 text-sm text-zinc-300">
              <div className="bg-zinc-950 p-4 rounded-xl border border-zinc-800 space-y-2">
                <div><span className="text-zinc-500 text-xs">Comando:</span></div>
                <div className="font-mono text-xs text-emerald-400 bg-zinc-900 p-2 rounded border border-zinc-800/80 overflow-x-auto">
                  {pendingConfirmation.command}
                </div>
                <div className="flex justify-between items-center text-xs pt-1">
                  <span className="text-zinc-400">Nível de risco:</span>
                  <span className="px-2 py-0.5 rounded font-bold bg-amber-500/20 text-amber-400 border border-amber-500/35">
                    Nível {pendingConfirmation.riskLevel} ({pendingConfirmation.reason})
                  </span>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-400 block mb-1">Deseja permitir?</label>
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={() => handleConfirmChoice('y')}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2.5 rounded-xl font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>[y] Sim, executar</span>
                  </button>
                  <button
                    onClick={() => handleConfirmChoice('n')}
                    className="flex-1 bg-red-600/80 hover:bg-red-600 text-white py-2.5 rounded-xl font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg"
                  >
                    <AlertCircle className="w-4 h-4" />
                    <span>[n] Não, cancelar</span>
                  </button>
                </div>
                
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-400 font-mono">Sua escolha:</span>
                  <input
                    type="text"
                    value={confirmInput}
                    onChange={(e) => setConfirmInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleConfirmChoice(confirmInput)}
                    placeholder="Digite y, s, sim, n, não..."
                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 text-xs font-mono text-zinc-100 focus:outline-none focus:border-[#d97757]"
                    autoFocus
                  />
                  <button
                    onClick={() => handleConfirmChoice(confirmInput)}
                    className="bg-[#d97757] hover:bg-[#c26749] text-white px-4 py-2 rounded-lg text-xs font-medium transition-colors"
                  >
                    Confirmar
                  </button>
                </div>
                {confirmError && (
                  <p className="text-xs text-red-400 mt-2 bg-red-950/40 p-2 rounded border border-red-900/50">{confirmError}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* /home Configuration Modal */}
      {homeModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl animate-in fade-in zoom-in duration-200 font-mono">
            
            <div className="text-center space-y-1 bg-zinc-950 p-3 rounded-xl border border-zinc-800">
              <div className="text-zinc-500 text-xs">╭──────────────────────────────────────────────╮</div>
              <div className="text-zinc-100 font-bold text-sm tracking-wider">CONFIGURAR DIRETÓRIO PADRÃO</div>
              <div className="text-zinc-500 text-xs">╰──────────────────────────────────────────────╯</div>
            </div>

            <div className="space-y-4 text-xs text-zinc-300">
              <div>
                <span className="text-zinc-400 block mb-1">Diretório atual:</span>
                <div className="bg-zinc-950 p-3 rounded-xl border border-zinc-800 text-emerald-400 break-all">
                  {currentWorkspaceDir || 'Carregando...'}
                </div>
              </div>

              <form onSubmit={handleSaveWorkspaceHome} className="space-y-3">
                <div>
                  <label className="text-zinc-400 block mb-1">Digite o novo diretório:</label>
                  <div className="flex items-center bg-zinc-950 border border-zinc-800 rounded-xl px-3 py-2 text-zinc-100 focus-within:border-[#d97757]">
                    <span className="text-[#d97757] font-bold mr-2">&gt;</span>
                    <input
                      type="text"
                      value={newWorkspaceDirInput}
                      onChange={(e) => setNewWorkspaceDirInput(e.target.value)}
                      placeholder="/data/data/com.termux/files/home ou /caminho/absoluto..."
                      className="w-full bg-transparent border-none text-xs text-zinc-100 focus:outline-none"
                      autoFocus
                    />
                  </div>
                </div>

                {homeResultMsg && (
                  <div className="bg-emerald-950/40 border border-emerald-900/50 p-3 rounded-xl text-emerald-300 whitespace-pre-wrap leading-relaxed">
                    {homeResultMsg}
                  </div>
                )}

                {homeResultError && (
                  <div className="bg-red-950/40 border border-red-900/50 p-3 rounded-xl text-red-300 whitespace-pre-wrap leading-relaxed">
                    {homeResultError}
                  </div>
                )}

                <div className="flex gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={loadingConfig || !newWorkspaceDirInput.trim()}
                    className="flex-1 bg-[#d97757] hover:bg-[#c26749] disabled:opacity-50 text-white py-2.5 rounded-xl font-medium text-xs flex items-center justify-center gap-1.5 transition-colors shadow-lg"
                  >
                    <span>Salvar & Aplicar</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setHomeModalOpen(false)}
                    className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-5 py-2.5 rounded-xl font-medium text-xs transition-colors"
                  >
                    Fechar
                  </button>
                </div>
              </form>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}

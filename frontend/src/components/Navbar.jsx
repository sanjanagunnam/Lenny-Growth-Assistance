import React, { useState, useRef, useEffect } from 'react';
import { 
  Cpu, 
  Sparkle, 
  Database, 
  Circle, 
  SidebarSimple, 
  Article, 
  ChatCircleText, 
  ArrowsClockwise,
  Layout,
  CaretDown,
  Check,
  Lightning,
  ArrowRight,
  House
} from '@phosphor-icons/react';

const OLLAMA_MODELS = [
  { 
    id: 'glm-5.3-flash', 
    label: 'GLM-5.3-Flash', 
    tag: 'Fast • Default', 
    icon: Lightning, 
    desc: 'Ultra-fast growth & product reasoning model' 
  },
  { 
    id: 'llama3.2', 
    label: 'Llama 3.2 3B', 
    tag: 'Meta Instruct', 
    icon: Cpu, 
    desc: 'Meta 3B high-density instruction model' 
  },
  { 
    id: 'phi3', 
    label: 'Phi-3 Mini 128k', 
    tag: 'Reasoning', 
    icon: Cpu, 
    desc: 'Microsoft 128k context product reasoning' 
  },
  { 
    id: 'qwen2.5', 
    label: 'Qwen 2.5 3B', 
    tag: 'Operator', 
    icon: Cpu, 
    desc: 'Alibaba high-speed operator model' 
  },
  { 
    id: 'mistral', 
    label: 'Mistral 7B', 
    tag: 'Dense', 
    icon: Cpu, 
    desc: 'Dense European startup instruction model' 
  },
];

const GROQ_MODELS = [
  {
    id: 'openai/gpt-oss-120b',
    label: 'GPT-OSS 120B',
    tag: '⚡ 500 t/s • FREE',
    desc: 'Flagship 120B reasoning model on Groq LPU',
  },
  {
    id: 'openai/gpt-oss-20b',
    label: 'GPT-OSS 20B Instant',
    tag: '⚡ Ultra-Fast',
    desc: 'Fastest model on Groq — sub-second responses',
  },
  {
    id: 'qwen/qwen3.8-27b',
    label: 'Qwen 3.8 27B',
    tag: 'Dense • Reasoning',
    desc: 'Dense product operator & strategy reasoning',
  },
  {
    id: 'groq/compound',
    label: 'Groq Compound',
    tag: 'Compound AI',
    desc: 'Compound AI multi-system reasoning',
  },
];

const CLAUDE_MODELS = [
  {
    id: 'claude-sonnet-5-latest',
    label: 'Claude Sonnet 5',
    tag: 'Balanced • Fast',
    desc: 'Latest Sonnet — fast, intelligent, balanced',
  },
  {
    id: 'claude-haiku-4-5-latest',
    label: 'Claude Haiku 4.5',
    tag: 'Ultra-Fast',
    desc: 'Ultra-fast, low-latency for quick answers',
  },
  {
    id: 'claude-opus-5-latest',
    label: 'Claude Opus 5',
    tag: 'Most Capable',
    desc: 'Most capable — deep reasoning & analysis',
  },
  {
    id: 'claude-fable-5-1-latest',
    label: 'Claude Fable 5.1',
    tag: 'Creative',
    desc: 'Creative writing & nuanced storytelling',
  },
];

const GEMINI_MODELS = [
  {
    id: 'gemini-3.8-flash',
    label: 'Gemini 3.8 Flash',
    tag: '⚡ Google • Accurate',
    desc: 'Google flagship intelligence — zero hallucinations, live world knowledge',
  },
  {
    id: 'gemini-3.6-flash',
    label: 'Gemini 3.6 Flash',
    tag: 'High-Speed',
    desc: 'Ultra high-speed generation with broad factual accuracy',
  },
];

export default function Navbar({
  currentView = 'landing',
  setCurrentView,
  provider,
  setProvider,
  model,
  setModel,
  mode,
  setMode,
  health,
  onToggleSidebar,
  onToggleCanvas,
  isCanvasOpen,
  hasActiveArtifact,
  onGoHome,
}) {
  const isOllama = provider === 'ollama';
  const isClaude = provider === 'anthropic';
  const isGroq = provider === 'groq';
  const isGemini = provider === 'gemini';
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeOllamaModel = OLLAMA_MODELS.find((m) => m.id === model) || OLLAMA_MODELS[0];
  const activeClaudeModel = CLAUDE_MODELS.find((m) => m.id === model) || CLAUDE_MODELS[0];
  const activeGroqModel = GROQ_MODELS.find((m) => m.id === model) || GROQ_MODELS[0];
  const activeGeminiModel = GEMINI_MODELS.find((m) => m.id === model) || GEMINI_MODELS[0];
  const activeModelLabel = isOllama ? activeOllamaModel.label : isClaude ? activeClaudeModel.label : isGemini ? activeGeminiModel.label : activeGroqModel.label;
  const activeModels = isOllama ? OLLAMA_MODELS : isClaude ? CLAUDE_MODELS : isGemini ? GEMINI_MODELS : GROQ_MODELS;

  // LANDING PAGE HEADER
  if (currentView === 'landing') {
    return (
      <header className="h-16 fixed top-0 inset-x-0 border-b border-white/5 bg-[#090d16]/90 backdrop-blur-2xl px-5 sm:px-10 flex items-center justify-between select-none z-50">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-500 via-indigo-500 to-purple-500 p-0.5 shadow-lg shadow-sky-500/25 shrink-0">
            <div className="w-full h-full bg-[#090d16] rounded-[10px] flex items-center justify-center text-sky-400">
              <Sparkle size={18} weight="fill" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-base font-bold text-white tracking-tight">Lenny AI</span>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/15 text-sky-400 border border-sky-500/25">v1.0</span>
          </div>
        </div>

        {/* Center Nav Tabs */}
        <div className="hidden md:flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.04] border border-white/8 text-xs font-medium">
          <button
            onClick={() => setCurrentView?.('landing')}
            className="px-3.5 py-1.5 rounded-lg bg-white/10 text-white shadow-sm font-semibold transition-all"
          >
            Overview & Architecture
          </button>
          <button
            onClick={() => setCurrentView?.('chat')}
            className="px-3.5 py-1.5 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            Chat Workspace
          </button>
        </div>

        {/* Right Action & Connectivity Indicator */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/8 text-xs font-mono text-slate-300">
            <span className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span>{health?.status === 'healthy' ? 'RAG Stack Live' : 'Connecting...'}</span>
          </div>

          <button
            onClick={() => setCurrentView?.('chat')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-600 hover:from-sky-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-sky-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <ChatCircleText size={16} weight="fill" />
            <span>Open Chat</span>
            <ArrowRight size={14} weight="bold" />
          </button>
        </div>
      </header>
    );
  }

  // CHAT WORKSPACE HEADER
  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur px-4 flex items-center justify-between select-none z-30">
      {/* Left section: Sidebar toggle & Branding */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={onToggleSidebar}
          aria-label="Toggle Sessions Sidebar"
          className="p-1.5 rounded-md hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <SidebarSimple size={18} weight="bold" />
        </button>

        <button
          onClick={() => setCurrentView?.('landing')}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-300 hover:text-white transition-all text-xs font-medium"
          title="Back to Landing Page Overview"
        >
          <House size={14} />
          <span className="hidden sm:inline">Overview</span>
        </button>

        <button
          onClick={onGoHome}
          className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
          title="Reset Active Session"
        >
          <div className="w-6 h-6 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Sparkle size={14} weight="fill" />
          </div>
          <div className="hidden lg:flex items-center gap-2">
            <span className="font-semibold text-sm tracking-tight text-zinc-100">
              Lenny AI
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300">
              v1.0
            </span>
          </div>
        </button>
      </div>

      {/* Middle section: Mode selector */}
      <div className="hidden md:flex items-center gap-2 bg-zinc-900 border border-zinc-800 p-0.5 rounded-lg">
        <button
          onClick={() => setMode('chat')}
          className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all ${
            mode === 'chat'
              ? 'bg-zinc-800 text-zinc-100 shadow-sm border border-zinc-700/50'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <ChatCircleText size={14} weight={mode === 'chat' ? 'fill' : 'regular'} />
          Standard PM Chat
        </button>
        <button
          onClick={() => setMode('ship30')}
          className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-md transition-all ${
            mode === 'ship30'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm font-semibold'
              : 'text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <Article size={14} weight={mode === 'ship30' ? 'fill' : 'regular'} />
          Ship 30 for 30 Engine
        </button>
      </div>

      {/* Right section: Model selector & Live Health Status */}
      <div className="flex items-center gap-3">
        {/* Subsystem Health Indicators */}
        <div className="hidden lg:flex items-center gap-3 px-2.5 py-1 rounded-md bg-zinc-900/60 border border-zinc-800 text-xs font-mono">
          {/* DB Indicator */}
          <div className="flex items-center gap-1.5" title={health.database ? "PostgreSQL & pgvector Healthy" : "Database Offline / Connecting"}>
            <Database size={13} className={health.database ? "text-emerald-400" : "text-rose-400"} />
            <span className="text-[11px] text-zinc-400">pgvector</span>
            <Circle size={6} weight="fill" className={health.database ? "text-emerald-400 animate-pulse" : "text-rose-500"} />
          </div>

          <div className="w-px h-3 bg-zinc-800" />

          {/* Ollama Indicator */}
          <div className="flex items-center gap-1.5" title={health.ollama ? "Ollama Daemon Connected" : "Ollama Daemon Offline"}>
            <Cpu size={13} className={health.ollama ? "text-emerald-400" : "text-amber-500"} />
            <span className="text-[11px] text-zinc-400">ollama</span>
            <Circle size={6} weight="fill" className={health.ollama ? "text-emerald-400 animate-pulse" : "text-amber-500"} />
          </div>
        </div>

        {/* Dynamic Provider & Model Selector */}
        <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-md p-0.5 gap-1">
          {/* Provider Toggle: Gemini ✨ */}
          <button
            onClick={() => {
              setProvider('gemini');
              setModel('gemini-3.8-flash');
              setIsDropdownOpen(false);
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded transition-colors ${
              isGemini
                ? 'bg-zinc-800 text-amber-300 font-medium border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sparkle size={13} weight={isGemini ? 'fill' : 'regular'} className={isGemini ? 'text-blue-400' : 'text-zinc-400'} />
            <span>Gemini</span>
            {isGemini && <span className="text-[9px] px-1 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded">PRO</span>}
          </button>

          {/* Provider Toggle: Groq ⚡ */}
          <button
            onClick={() => {
              setProvider('groq');
              setModel('openai/gpt-oss-120b');
              setIsDropdownOpen(false);
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded transition-colors ${
              isGroq
                ? 'bg-zinc-800 text-amber-300 font-medium border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Lightning size={13} weight="fill" />
            <span>Groq</span>
            {isGroq && <span className="text-[9px] px-1 py-0.5 bg-green-500/10 text-green-400 border border-green-500/30 rounded">FREE</span>}
          </button>

          {/* Provider Toggle: Ollama */}
          <button
            onClick={() => {
              setProvider('ollama');
              setModel('glm-5.3-flash');
              setIsDropdownOpen(false);
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded transition-colors ${
              isOllama
                ? 'bg-zinc-800 text-amber-300 font-medium border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Cpu size={13} />
            <span>Ollama</span>
          </button>

          {/* Provider Toggle: Claude */}
          <button
            onClick={() => {
              setProvider('anthropic');
              setModel('claude-sonnet-5-latest');
              setIsDropdownOpen(false);
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded transition-colors ${
              isClaude
                ? 'bg-zinc-800 text-amber-300 font-medium border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sparkle size={13} />
            <span>Claude</span>
          </button>

          {/* Model Dropdown (works for all providers) */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              id="model-selector-dropdown-btn"
              className="flex items-center gap-1.5 px-2 py-1 text-xs font-mono rounded bg-zinc-950/80 border border-amber-500/30 text-amber-300 hover:border-amber-400 transition-colors"
              title="Select Model"
            >
              <Lightning size={12} weight="fill" className="text-amber-400" />
              <span className="font-semibold max-w-[120px] truncate">{activeModelLabel}</span>
              <CaretDown size={11} className={`text-zinc-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {isDropdownOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-72 bg-zinc-950 border border-zinc-800 rounded-lg shadow-2xl py-1.5 z-50 animate-in fade-in zoom-in-95">
                <div className="px-3 py-1 text-[10px] uppercase font-mono tracking-wider text-zinc-500 border-b border-zinc-800/80 mb-1">
                  {isOllama ? 'Ollama Local Models' : isGroq ? 'Groq Cloud ⚡ Ultra-Fast (FREE)' : isGemini ? 'Google Gemini ⚡ World Knowledge' : 'Claude Cloud Models'}
                </div>
                {activeModels.map((m) => {
                  const isSelected = model === m.id;
                  return (
                    <button
                      key={m.id}
                      id={`model-option-${m.id}`}
                      onClick={() => {
                        setModel(m.id);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left transition-colors ${
                        isSelected
                          ? 'bg-amber-500/10 text-amber-300 font-medium'
                          : 'text-zinc-300 hover:bg-zinc-900 hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Check size={12} className={isSelected ? 'text-amber-400 opacity-100' : 'opacity-0'} />
                        <div>
                          <div className="font-medium text-xs flex items-center gap-1.5">
                            <span>{m.label}</span>
                            {(m.id === 'glm-5.3-flash' || m.id === 'claude-sonnet-5-latest' || m.id === 'openai/gpt-oss-120b') && (
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                            )}
                          </div>
                          <div className="text-[10px] text-zinc-500 font-mono">{m.desc}</div>
                        </div>
                      </div>
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border shrink-0 ${
                        isSelected
                          ? 'bg-amber-500/20 border-amber-500/30 text-amber-300'
                          : 'bg-zinc-900 border-zinc-800 text-zinc-400'
                      }`}>
                        {m.tag}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Canvas Drawer Toggle Button */}
        <button
          onClick={onToggleCanvas}
          title={isCanvasOpen ? "Collapse Growth Canvas" : "Expand Growth Canvas"}
          className={`flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-md border transition-all ${
            isCanvasOpen
              ? 'bg-amber-500/10 border-amber-500/40 text-amber-400 font-medium'
              : hasActiveArtifact
              ? 'bg-zinc-900 border-zinc-700 text-zinc-200 hover:border-amber-500/30'
              : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:text-zinc-300'
          }`}
        >
          <Layout size={14} weight={isCanvasOpen ? "fill" : "regular"} />
          <span className="hidden sm:inline">Canvas</span>
          {hasActiveArtifact && !isCanvasOpen && (
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
          )}
        </button>
      </div>
    </header>
  );
}

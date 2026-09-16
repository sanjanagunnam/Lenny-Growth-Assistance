import React from 'react';
import { 
  Cpu, 
  Sparkle, 
  Database, 
  Circle, 
  SidebarSimple, 
  Article, 
  ChatCircleText, 
  ArrowsClockwise,
  Layout
} from '@phosphor-icons/react';

export default function Navbar({
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
}) {
  const isOllama = provider === 'ollama';

  return (
    <header className="h-14 border-b border-zinc-800 bg-zinc-950/90 backdrop-blur px-4 flex items-center justify-between select-none z-30">
      {/* Left section: Sidebar toggle & Branding */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          aria-label="Toggle Sessions Sidebar"
          className="p-1.5 rounded-md hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          <SidebarSimple size={18} weight="bold" />
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Sparkle size={14} weight="fill" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm tracking-tight text-zinc-100">
                Lenny Growth Assistant
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-300">
                v1.0
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle section: Mode selector & Telemetry */}
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
            <Circle size={6} weight="fill" className={health.ollama ? "text-emerald-400" : "text-amber-500"} />
          </div>
        </div>

        {/* Dynamic Provider Selector */}
        <div className="flex items-center bg-zinc-900 border border-zinc-800 rounded-md p-0.5">
          <button
            onClick={() => {
              setProvider('ollama');
              setModel('llama3.2');
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded transition-colors ${
              isOllama
                ? 'bg-zinc-800 text-amber-300 font-medium border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Cpu size={13} />
            <span>Ollama (Llama 3.2)</span>
          </button>
          <button
            onClick={() => {
              setProvider('anthropic');
              setModel('claude-3-5-sonnet-latest');
            }}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded transition-colors ${
              !isOllama
                ? 'bg-zinc-800 text-amber-300 font-medium border border-zinc-700'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Sparkle size={13} />
            <span>Claude 3.5</span>
          </button>
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

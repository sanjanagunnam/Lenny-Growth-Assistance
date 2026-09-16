import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ArtifactViewer from './components/ArtifactViewer';
import { WarningCircle, Lightning, ArrowClockwise, X } from '@phosphor-icons/react';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [provider, setProvider] = useState('ollama');
  const [model, setModel] = useState('glm-5.3-flash');
  const [mode, setMode] = useState('chat'); // 'chat' | 'ship30'
  const [activeArtifact, setActiveArtifact] = useState(null);
  const [isCanvasOpen, setIsCanvasOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorBanner, setErrorBanner] = useState(null);
  const [circuitBreakerToast, setCircuitBreakerToast] = useState(null); // { message, lastPrompt }

  const [health, setHealth] = useState({
    status: 'healthy',
    database: true,
    ollama: true,
    providers_available: ['ollama'],
  });

  // 1. Health Diagnostics Polling
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('/healthz');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      }
    } catch {
      setHealth((prev) => ({ ...prev, status: 'degraded', database: false, ollama: false }));
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // 2. Fetch Sessions List
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/sessions');
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // 3. Load Active Session Messages
  const loadSession = useCallback(async (sessionId) => {
    if (!sessionId) {
      setActiveSessionId(null);
      setMessages([]);
      return;
    }
    setActiveSessionId(sessionId);
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        const loadedMessages = data.messages || [];
        setMessages(loadedMessages);

        // Find latest artifact if present
        const lastWithArtifact = [...loadedMessages].reverse().find(
          (m) => m.artifact_content || (m.artifact && m.artifact.content)
        );
        if (lastWithArtifact) {
          const art = lastWithArtifact.artifact || {
            type: lastWithArtifact.artifact_type || 'markdown',
            title: 'Generated Artifact',
            content: lastWithArtifact.artifact_content,
          };
          setActiveArtifact(art);
        }
      }
    } catch (err) {
      console.error('Failed to load session history:', err);
    }
  }, []);

  // 4. Create New Session
  const handleNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
    setActiveArtifact(null);
    setIsCanvasOpen(false);
    setErrorBanner(null);
  };

  // 5. Send Message & Chat Generation
  const handleSendMessage = async (text, overrideMode = null, overrideProvider = null) => {
    setErrorBanner(null);
    setIsGenerating(true);

    const activeMode = overrideMode || mode;
    if (overrideMode && overrideMode !== mode) {
      setMode(overrideMode);
    }

    const activeProvider = overrideProvider || provider;
    if (overrideProvider && overrideProvider !== provider) {
      setProvider(overrideProvider);
      if (overrideProvider === 'anthropic') {
        setModel('claude-3-5-sonnet-latest');
      }
    }

    // Optimistically append user message
    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const payload = {
        message: text,
        session_id: activeSessionId || undefined,
        provider: activeProvider,
        model: activeProvider === 'anthropic' ? 'claude-3-5-sonnet-latest' : model,
        mode: activeMode,
      };

      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const detailMsg =
          errData?.detail?.message ||
          errData?.detail?.suggestion ||
          errData?.message ||
          `Request failed with status ${res.status}`;

        // Circuit breaker check: If 504 or timeout error from Ollama
        if (res.status === 504 || errData?.detail?.error === 'LLM_TIMEOUT' || detailMsg.toLowerCase().includes('timed out')) {
          setCircuitBreakerToast({
            message: detailMsg,
            lastPrompt: text,
          });
        }
        throw new Error(detailMsg);
      }

      const data = await res.json();

      // Successful response dismisses circuit breaker toast
      setCircuitBreakerToast(null);

      // Append assistant message with grounding telemetry
      const assistantMsg = {
        id: data.message_id || Date.now() + 1,
        role: 'assistant',
        content: data.reply,
        provider: data.provider_used,
        sources: data.sources || [],
        artifact: data.artifact,
        grounding_confidence: data.grounding_confidence,
        epistemic_status: data.epistemic_status,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);

      // If active session wasn't set, update it
      if (data.session_id && data.session_id !== activeSessionId) {
        setActiveSessionId(data.session_id);
        fetchSessions();
      }

      // If an artifact was emitted, open Canvas drawer automatically
      if (data.artifact) {
        setActiveArtifact(data.artifact);
        setIsCanvasOpen(true);
      }
    } catch (err) {
      console.error('Chat error:', err);
      setErrorBanner(err.message);
      // Append warning bubble in chat
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'assistant',
          content: `⚠️ **Operational Alert**: ${err.message}`,
          sources: [],
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSwitchToClaudeAndRetry = () => {
    if (!circuitBreakerToast?.lastPrompt) return;
    const promptToRetry = circuitBreakerToast.lastPrompt;
    setCircuitBreakerToast(null);
    setErrorBanner(null);
    setProvider('anthropic');
    setModel('claude-3-5-sonnet-latest');
    handleSendMessage(promptToRetry, mode, 'anthropic');
  };

  const handleOpenArtifact = (art) => {
    setActiveArtifact(art);
    setIsCanvasOpen(true);
  };

  return (
    <div className="min-h-[100dvh] h-[100dvh] bg-zinc-950 text-zinc-100 flex flex-col overflow-hidden font-sans">
      {/* Top Navbar */}
      <Navbar
        provider={provider}
        setProvider={setProvider}
        model={model}
        setModel={setModel}
        mode={mode}
        setMode={setMode}
        health={health}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        onToggleCanvas={() => setIsCanvasOpen((prev) => !prev)}
        isCanvasOpen={isCanvasOpen}
        hasActiveArtifact={!!activeArtifact}
      />

      {/* Global Alert Banner if degraded */}
      {errorBanner && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-4 py-1.5 text-xs text-amber-300 flex items-center justify-between font-mono">
          <div className="flex items-center gap-2">
            <WarningCircle size={14} weight="bold" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-amber-400 hover:text-amber-200 text-xs"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Circuit Breaker Non-Blocking Toast Banner */}
      {circuitBreakerToast && (
        <aside
          aria-label="Operational Alert"
          className="fixed bottom-20 right-6 z-50 max-w-md w-full p-4 rounded-xl bg-zinc-900 border border-amber-500/40 shadow-2xl shadow-amber-500/10 backdrop-blur-md flex flex-col gap-3 animate-in fade-in slide-in-from-bottom-4 duration-200"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2.5">
              <div className="w-6 h-6 rounded-md bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 flex-shrink-0 mt-0.5">
                <Lightning size={14} weight="fill" />
              </div>
              <div>
                <h4 className="text-xs font-semibold text-zinc-100 mb-0.5">
                  Local Model Timeout (15s Circuit Breaker)
                </h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed">
                  {circuitBreakerToast.message}
                </p>
              </div>
            </div>
            <button
              onClick={() => setCircuitBreakerToast(null)}
              className="text-zinc-500 hover:text-zinc-300 p-1"
            >
              <X size={14} />
            </button>
          </div>

          <div className="flex items-center justify-end gap-2 pt-1 border-t border-zinc-800/80">
            <button
              onClick={() => setCircuitBreakerToast(null)}
              className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors"
            >
              Dismiss
            </button>
            <button
              onClick={handleSwitchToClaudeAndRetry}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-zinc-950 text-xs font-semibold transition-all shadow-sm"
            >
              <ArrowClockwise size={13} weight="bold" />
              <span>Switch to Claude & Retry</span>
            </button>
          </div>
        </aside>
      )}

      {/* Main Split-View Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar */}
        <Sidebar
          isOpen={isSidebarOpen}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={loadSession}
          onNewSession={handleNewSession}
          onCloseMobile={() => setIsSidebarOpen(false)}
        />

        {/* Center / Left Pane: Chat Stream */}
        <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
          <ChatWindow
            messages={messages}
            isGenerating={isGenerating}
            onSendMessage={handleSendMessage}
            onOpenArtifact={handleOpenArtifact}
            activeArtifact={activeArtifact}
            mode={mode}
          />
        </main>

        {/* Right Pane: Growth Canvas / Artifact Drawer */}
        <ArtifactViewer
          artifact={activeArtifact}
          isOpen={isCanvasOpen}
          onClose={() => setIsCanvasOpen(false)}
        />
      </div>
    </div>
  );
}

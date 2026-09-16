import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ArtifactViewer from './components/ArtifactViewer';
import { 
  Sparkle, 
  TrendUp,
  WarningCircle, 
  ArrowClockwise,
} from '@phosphor-icons/react';

const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [provider, setProvider] = useState('groq');
  const [model, setModel] = useState('openai/gpt-oss-120b');
  const [mode, setMode] = useState('chat'); // 'chat' | 'ship30'
  const [activeArtifact, setActiveArtifact] = useState(null);
  const [isCanvasOpen, setIsCanvasOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [generatingSessions, setGeneratingSessions] = useState({}); // { [sessionId]: boolean }
  const [errorBanner, setErrorBanner] = useState(null);
  const [circuitBreakerToast, setCircuitBreakerToast] = useState(null);

  // Keep a ref to activeSessionId for async closures
  const activeSessionRef = useRef(activeSessionId);
  useEffect(() => {
    activeSessionRef.current = activeSessionId;
  }, [activeSessionId]);

  // Derive whether the currently viewed conversation is generating
  const isCurrentGenerating = !!(activeSessionId && generatingSessions[activeSessionId]);

  // Per-conversation message cache to avoid refetching on switch
  const conversationCache = useRef({});

  const [health, setHealth] = useState({
    status: 'healthy',
    database: true,
    ollama: true,
    providers_available: ['ollama', 'anthropic'],
  });

  // 1. Health Diagnostics Polling
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/healthz`);
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
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  // 2. Fetch Sessions List
  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions`);
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

  // 3. Create New Session — fully isolates state immediately
  const handleNewSession = useCallback(() => {
    // Cache current conversation before creating new
    if (activeSessionId && messages.length > 0) {
      conversationCache.current[activeSessionId] = {
        messages: [...messages],
        artifact: activeArtifact,
      };
    }
    setActiveSessionId(null);
    activeSessionRef.current = null;
    setMessages([]);
    setActiveArtifact(null);
    setIsCanvasOpen(false);
    setErrorBanner(null);
    setCircuitBreakerToast(null);
  }, [activeSessionId, messages, activeArtifact]);

  // 4. Load Active Session Messages (with instant cache + guaranteed authoritative fetch)
  const loadSession = useCallback(async (sessionId) => {
    if (!sessionId) {
      handleNewSession();
      return;
    }
    if (activeSessionId === sessionId) return;

    // Save current conversation to cache before switching
    if (activeSessionId && messages.length > 0) {
      conversationCache.current[activeSessionId] = {
        messages: [...messages],
        artifact: activeArtifact,
      };
    }

    setActiveSessionId(sessionId);
    activeSessionRef.current = sessionId;
    setErrorBanner(null);

    // 1. Check cache first for instant switch
    if (conversationCache.current[sessionId]?.messages?.length > 0) {
      const cached = conversationCache.current[sessionId];
      setMessages(cached.messages);
      if (cached.artifact) {
        setActiveArtifact(cached.artifact);
      } else {
        setActiveArtifact(null);
        setIsCanvasOpen(false);
      }
    } else {
      setMessages([]);
      setActiveArtifact(null);
      setIsCanvasOpen(false);
    }

    // 2. Authoritative fetch from server to guarantee completed answers are displayed
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        const loadedMessages = data.messages || [];

        // Find latest artifact if present
        const lastWithArtifact = [...loadedMessages].reverse().find(
          (m) => m.artifact_content || (m.artifact && m.artifact.content)
        );
        const art = lastWithArtifact
          ? (lastWithArtifact.artifact || {
              type: lastWithArtifact.artifact_type || 'markdown',
              title: 'Generated Artifact',
              content: lastWithArtifact.artifact_content,
            })
          : null;

        // Update cache with authoritative backend data
        conversationCache.current[sessionId] = {
          messages: loadedMessages,
          artifact: art,
        };

        // ONLY update the active screen if the user is STILL looking at this session
        if (activeSessionRef.current === sessionId) {
          setMessages(loadedMessages);
          if (art) {
            setActiveArtifact(art);
          } else {
            setActiveArtifact(null);
            setIsCanvasOpen(false);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load session history:', err);
    }
  }, [activeSessionId, messages, activeArtifact, handleNewSession]);

  // 5. Delete Session
  const handleDeleteSession = useCallback(async (sessionId) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, { method: 'DELETE' });
      if (res.ok || res.status === 204) {
        // Remove from cache
        delete conversationCache.current[sessionId];
        // If deleting active session, clear state
        if (sessionId === activeSessionId) {
          setActiveSessionId(null);
          activeSessionRef.current = null;
          setMessages([]);
          setActiveArtifact(null);
          setIsCanvasOpen(false);
        }
        // Refresh sessions list
        fetchSessions();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }, [activeSessionId, fetchSessions]);

  // 6. Send Message & Chat Generation (Multi-Thread Concurrent & Strictly Isolated)
  const handleSendMessage = async (text, overrideMode = null, overrideProvider = null) => {
    setErrorBanner(null);

    const activeMode = overrideMode || mode;
    if (overrideMode && overrideMode !== mode) {
      setMode(overrideMode);
    }

    const activeProvider = overrideProvider || provider;
    if (overrideProvider && overrideProvider !== provider) {
      setProvider(overrideProvider);
      if (overrideProvider === 'anthropic') {
        setModel('claude-3-5-sonnet-20241022');
      }
    }

    // Resolve target session ID: either current active session or a brand new unique ID
    const targetSessionId = activeSessionId || `sess_${Date.now()}`;
    if (!activeSessionId) {
      setActiveSessionId(targetSessionId);
      activeSessionRef.current = targetSessionId;
    }

    // Mark this specific session as generating in background
    setGeneratingSessions((prev) => ({ ...prev, [targetSessionId]: true }));

    // Optimistically create user message
    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };

    // Update conversation cache for target session
    const prevCached = conversationCache.current[targetSessionId]?.messages || [];
    const updatedMessages = [...prevCached, tempUserMsg];
    conversationCache.current[targetSessionId] = {
      messages: updatedMessages,
      artifact: conversationCache.current[targetSessionId]?.artifact || null,
    };

    // ONLY update screen if user is currently looking at this session
    if (activeSessionRef.current === targetSessionId) {
      setMessages(updatedMessages);
    }

    try {
      const payload = {
        message: text,
        session_id: targetSessionId,
        provider: activeProvider,
        model: model,
        mode: activeMode,
      };

      const res = await fetch(`${API_BASE}/api/v1/chat`, {
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

      // Construct assistant message
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

      // Update cache for this session
      const currentHistory = conversationCache.current[targetSessionId]?.messages || [];
      const finalMessages = [...currentHistory.filter(m => m.id !== tempUserMsg.id), tempUserMsg, assistantMsg];
      conversationCache.current[targetSessionId] = {
        messages: finalMessages,
        artifact: data.artifact || conversationCache.current[targetSessionId]?.artifact || null,
      };

      // Refresh session list so updated title and message counts appear in sidebar
      fetchSessions();

      // ONLY update the active screen if the user is STILL on targetSessionId!
      if (activeSessionRef.current === targetSessionId) {
        setMessages(finalMessages);
        if (data.artifact) {
          setActiveArtifact(data.artifact);
          setIsCanvasOpen(true);
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      const alertMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `⚠️ **Operational Alert**: ${err.message}`,
        sources: [],
        created_at: new Date().toISOString(),
      };
      const currentHistory = conversationCache.current[targetSessionId]?.messages || [];
      const finalMessages = [...currentHistory, alertMsg];
      conversationCache.current[targetSessionId] = {
        messages: finalMessages,
        artifact: conversationCache.current[targetSessionId]?.artifact || null,
      };

      if (activeSessionRef.current === targetSessionId) {
        setErrorBanner(err.message);
        setMessages(finalMessages);
      }
    } finally {
      // Clear generating status for this session
      setGeneratingSessions((prev) => {
        const next = { ...prev };
        delete next[targetSessionId];
        return next;
      });
    }
  };

  const handleSwitchToClaudeAndRetry = () => {
    if (!circuitBreakerToast?.lastPrompt) return;
    const promptToRetry = circuitBreakerToast.lastPrompt;
    setCircuitBreakerToast(null);
    setErrorBanner(null);
    setProvider('anthropic');
    setModel('claude-3-5-sonnet-20241022');
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
        onGoHome={handleNewSession}
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
                  Local Model Timeout (Circuit Breaker)
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
          generatingSessions={generatingSessions}
          onSelectSession={loadSession}
          onNewSession={handleNewSession}
          onDeleteSession={handleDeleteSession}
          onCloseMobile={() => setIsSidebarOpen(false)}
        />

        {/* Center / Left Pane: Chat Stream */}
        <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
          <ChatWindow
            messages={messages}
            isGenerating={isCurrentGenerating}
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

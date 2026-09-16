import React, { useState } from 'react';
import { 
  Plus, 
  ChatTeardropText, 
  Clock, 
  Trash, 
  CaretRight 
} from '@phosphor-icons/react';

export default function Sidebar({
  isOpen,
  sessions,
  activeSessionId,
  generatingSessions = {},
  onSelectSession,
  onNewSession,
  onDeleteSession,
  onCloseMobile,
}) {
  const [hoveredId, setHoveredId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const formatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return 'just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  const handleDeleteClick = (e, sessionId) => {
    e.stopPropagation();
    if (confirmDeleteId === sessionId) {
      // Second click = confirm delete
      onDeleteSession(sessionId);
      setConfirmDeleteId(null);
    } else {
      setConfirmDeleteId(sessionId);
      // Auto-reset confirm state after 3s
      setTimeout(() => setConfirmDeleteId(null), 3000);
    }
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden"
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 bg-zinc-950 border-r border-zinc-800/80 flex flex-col transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0 md:w-0 md:opacity-0 md:overflow-hidden'
        }`}
      >
        {/* Top: New Conversation Button */}
        <div className="p-3 border-b border-zinc-800/60">
          <button
            onClick={() => {
              onNewSession();
              if (onCloseMobile) onCloseMobile();
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 text-zinc-100 font-medium text-xs transition-all shadow-sm group"
          >
            <Plus size={14} weight="bold" className="text-amber-400 group-hover:scale-110 transition-transform" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Sessions List Header */}
        <div className="px-3 pt-3 pb-1 flex items-center justify-between text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
          <span>Persisted Threads</span>
          <span className="text-zinc-400">{sessions.length}</span>
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-2 py-1 space-y-0.5">
          {sessions.length === 0 ? (
            <div className="p-4 text-center text-xs text-zinc-400">
              No previous threads.
              <br />
              Start asking a question!
            </div>
          ) : (
            sessions.map((sess) => {
              const isActive = sess.id === activeSessionId;
              const isHovered = hoveredId === sess.id;
              const isConfirmDelete = confirmDeleteId === sess.id;
              return (
                <div
                  key={sess.id}
                  onMouseEnter={() => setHoveredId(sess.id)}
                  onMouseLeave={() => {
                    setHoveredId(null);
                    if (confirmDeleteId === sess.id) setConfirmDeleteId(null);
                  }}
                  className="relative"
                >
                  <button
                    onClick={() => {
                      onSelectSession(sess.id);
                      if (onCloseMobile) onCloseMobile();
                    }}
                    className={`w-full text-left p-2.5 rounded-lg text-xs transition-all group relative flex items-start justify-between gap-2 ${
                      isActive
                        ? 'bg-zinc-900 text-zinc-100 border border-zinc-800 shadow-sm'
                        : 'text-zinc-400 hover:bg-zinc-900/50 hover:text-zinc-200'
                    }`}
                  >
                    <div className="flex items-start gap-2 min-w-0 flex-1">
                      <ChatTeardropText
                        size={14}
                        className={`mt-0.5 flex-shrink-0 ${
                          isActive ? 'text-amber-400' : 'text-zinc-400 group-hover:text-zinc-400'
                        }`}
                        weight={isActive ? 'fill' : 'regular'}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-zinc-200 leading-tight">
                          {sess.title || 'Untitled Session'}
                        </p>
                        {generatingSessions[sess.id] ? (
                          <span className="text-[10px] font-mono text-amber-400 flex items-center gap-1.5 mt-0.5 animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                            <span>Thinking...</span>
                          </span>
                        ) : (
                          <span className="text-[10px] font-mono text-zinc-400 flex items-center gap-1 mt-0.5">
                            <Clock size={10} />
                            {formatTime(sess.updated_at || sess.created_at)}
                            {sess.messages?.length > 0 && (
                              <>
                                <span className="text-zinc-600">•</span>
                                <span>{sess.messages.length} msgs</span>
                              </>
                            )}
                          </span>
                        )}
                      </div>
                    </div>

                    {isActive && !isHovered && (
                      <CaretRight size={12} className="text-amber-400 mt-1 flex-shrink-0" />
                    )}
                  </button>

                  {/* Delete button - appears on hover */}
                  {(isHovered || isConfirmDelete) && (
                    <button
                      onClick={(e) => handleDeleteClick(e, sess.id)}
                      title={isConfirmDelete ? "Click again to confirm delete" : "Delete conversation"}
                      className={`absolute right-2 top-2.5 p-1 rounded transition-all ${
                        isConfirmDelete
                          ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                          : 'bg-zinc-800 text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent'
                      }`}
                    >
                      <Trash size={12} weight={isConfirmDelete ? 'fill' : 'regular'} />
                    </button>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Bottom Metadata */}
        <div className="p-3 border-t border-zinc-800/60 text-[11px] font-mono text-zinc-400 flex items-center justify-between">
          <span>PostgreSQL + pgvector</span>
          <span className="w-2 h-2 rounded-full bg-emerald-500/80" />
        </div>
      </aside>
    </>
  );
}

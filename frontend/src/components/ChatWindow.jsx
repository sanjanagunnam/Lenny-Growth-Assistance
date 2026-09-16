import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  PaperPlaneTilt, 
  Sparkle, 
  User, 
  BookBookmark, 
  Layout, 
  CaretDown, 
  CaretUp, 
  WarningCircle,
  Lightning
} from '@phosphor-icons/react';
import EmptyState from './EmptyState';

export default function ChatWindow({
  messages,
  isGenerating,
  onSendMessage,
  onOpenArtifact,
  activeArtifact,
  mode,
}) {
  const [input, setInput] = useState('');
  const [expandedSources, setExpandedSources] = useState({}); // messageId -> boolean
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isGenerating) return;
    onSendMessage(trimmed);
    setInput('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleSources = (msgId) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-zinc-950 overflow-hidden relative">
      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState 
            onSelectPreset={(presetPrompt, presetMode) => onSendMessage(presetPrompt, presetMode)} 
            mode={mode} 
          />
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            const hasSources = msg.sources && msg.sources.length > 0;
            const hasArtifact = msg.artifact_content || (msg.artifact && msg.artifact.content);
            const isSourcesExpanded = !!expandedSources[msg.id || index];

            // Grounding metrics calculation
            const isGrounded = msg.epistemic_status === 'GROUNDED';
            const isPartial = msg.epistemic_status === 'PARTIAL';
            const isRefusal = msg.epistemic_status === 'REFUSAL';
            const confidenceScore = msg.grounding_confidence != null && msg.grounding_confidence > 0
              ? msg.grounding_confidence
              : (hasSources ? (msg.sources.reduce((acc, s) => acc + (s.similarity || 0), 0) / msg.sources.length) : 0);
            const matchPct = Math.round(confidenceScore * 100);
            const citedEpisodes = [...new Set(msg.sources?.map(s => s.source_file) || [])];
            const citedCount = citedEpisodes.length || (hasSources ? msg.sources.length : 0);

            return (
              <div
                key={msg.id || index}
                className={`flex gap-3 max-w-3xl mx-auto ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                {/* Assistant Avatar */}
                {!isUser && (
                  <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0 mt-0.5">
                    <Sparkle size={14} weight="fill" />
                  </div>
                )}

                {/* Message Body */}
                <div className={`space-y-2 max-w-[88%] ${isUser ? 'items-end' : 'items-start'}`}>
                  {/* Inline Telemetry Badge for Assistant */}
                  {!isUser && (
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      {hasSources ? (
                        <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] border shadow-xs ${
                          isGrounded
                            ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                            : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${isGrounded ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                          <span className="font-semibold">{matchPct}% Match</span>
                          <span className="text-zinc-500">•</span>
                          <span>{citedCount} Episode{citedCount !== 1 ? 's' : ''} Cited</span>
                        </div>
                      ) : isRefusal ? (
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-[10px] border bg-zinc-900 border-zinc-800 text-zinc-400">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                          <span>Epistemic Guardrail • Refusal</span>
                        </div>
                      ) : null}

                      {msg.provider && (
                        <span className="font-mono text-[9px] text-zinc-500 px-1.5 py-0.5 rounded bg-zinc-900/60 border border-zinc-800">
                          {msg.provider}
                        </span>
                      )}
                    </div>
                  )}

                  <div
                    className={`p-4 rounded-xl text-xs leading-relaxed ${
                      isUser
                        ? 'bg-zinc-900 text-zinc-100 border border-zinc-800 shadow-sm ml-auto'
                        : 'bg-zinc-950 text-zinc-200 border border-zinc-800/80 shadow-sm'
                    }`}
                  >
                    {isUser ? (
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <div className="prose-custom">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>

                  {/* Grounding Citations Drawer */}
                  {!isUser && hasSources && (
                    <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/40 overflow-hidden text-[11px] w-full">
                      <button
                        onClick={() => toggleSources(msg.id || index)}
                        className="w-full px-3 py-1.5 flex items-center justify-between text-zinc-400 hover:text-zinc-200 transition-colors"
                      >
                        <div className="flex items-center gap-1.5 font-mono text-[10px] text-amber-400/90">
                          <BookBookmark size={12} weight="bold" />
                          <span>Grounded Sources ({msg.sources.length} transcript chunks • {citedCount} episodes)</span>
                        </div>
                        {isSourcesExpanded ? <CaretUp size={12} /> : <CaretDown size={12} />}
                      </button>

                      {isSourcesExpanded && (
                        <div className="p-2.5 pt-0 space-y-2 border-t border-zinc-800/60">
                          {msg.sources.map((s, sIdx) => {
                            const similarityPct = Math.round((s.similarity || 0.8) * 100);
                            const cleanEpisodeTitle = s.source_file.replace(/\.md$/, '').replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
                            return (
                              <div
                                key={sIdx}
                                className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800 text-zinc-300 font-mono text-[10px]"
                              >
                                <div className="flex items-center justify-between font-semibold text-zinc-200 mb-1 flex-wrap gap-1">
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-amber-300 font-bold">Guest: {s.guest_name || 'Interviewee'}</span>
                                    <span className="text-zinc-600">|</span>
                                    <span className="text-zinc-400 font-sans font-medium text-[11px]">{cleanEpisodeTitle}</span>
                                  </div>
                                  <span className="px-1.5 py-0.5 rounded bg-zinc-900 text-emerald-300 border border-zinc-700 font-mono text-[9px]">
                                    {similarityPct}% match
                                  </span>
                                </div>
                                <div className="text-zinc-300 line-clamp-3 text-[11px] font-sans leading-relaxed pl-2 border-l-2 border-amber-500/40 my-1.5 italic bg-zinc-900/30 py-1 rounded-r">
                                  "{s.content}"
                                </div>
                                <div className="text-zinc-500 text-[9px] truncate">
                                  File: {s.source_file} (Chunk {s.chunk_index || 1})
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Artifact Action Button */}
                  {!isUser && hasArtifact && (
                    <button
                      onClick={() => {
                        const artifactObj = msg.artifact || {
                          type: msg.artifact_type || 'markdown',
                          title: 'Generated Artifact',
                          content: msg.artifact_content || '',
                        };
                        onOpenArtifact(artifactObj);
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 font-medium text-xs transition-all shadow-sm group"
                    >
                      <Layout size={13} weight="bold" className="group-hover:scale-110 transition-transform" />
                      <span>Open in Canvas</span>
                      <span className="text-[10px] uppercase font-mono px-1 rounded bg-amber-500/20 text-amber-300">
                        {msg.artifact_type || (msg.artifact && msg.artifact.type) || 'asset'}
                      </span>
                    </button>
                  )}
                </div>

                {/* User Avatar */}
                {isUser && (
                  <div className="w-7 h-7 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-300 flex-shrink-0 mt-0.5">
                    <User size={14} weight="bold" />
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Loading / Generation Indicator */}
        {isGenerating && (
          <div className="flex gap-3 max-w-3xl mx-auto justify-start items-start">
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 animate-pulse">
              <Sparkle size={14} weight="fill" />
            </div>
            <div className="p-4 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-400 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
              <span>Synthesizing transcript evidence and generating response...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Bar */}
      <div className="p-4 border-t border-zinc-800 bg-zinc-950/80 backdrop-blur">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto relative rounded-xl bg-zinc-900 border border-zinc-800 focus-within:border-zinc-700 transition-all p-2"
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isGenerating}
            placeholder={
              mode === 'ship30'
                ? 'Specify a growth bottleneck or framework to draft a Ship 30 essay...'
                : 'Ask a growth or product question grounded in Lenny’s Podcast...'
            }
            rows={2}
            className="w-full bg-transparent text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none resize-none px-2 py-1 leading-relaxed"
          />

          <div className="flex items-center justify-between px-2 pt-1 border-t border-zinc-800/50">
            <div className="flex items-center gap-2 text-[10px] font-mono text-zinc-400">
              <span>Return to submit</span>
              <span>•</span>
              <span>Shift+Return for newline</span>
            </div>

            <button
              type="submit"
              disabled={!input.trim() || isGenerating}
              className={`p-1.5 rounded-lg flex items-center justify-center transition-all ${
                input.trim() && !isGenerating
                  ? 'bg-amber-500 hover:bg-amber-400 text-zinc-950 font-semibold shadow-sm'
                  : 'bg-zinc-800 text-zinc-400 cursor-not-allowed'
              }`}
            >
              <PaperPlaneTilt size={14} weight="bold" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

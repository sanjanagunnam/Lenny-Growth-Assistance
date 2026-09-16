import React from 'react';
import { 
  TrendUp, 
  Feather, 
  CodeBlock, 
  ShieldWarning, 
  ArrowUpRight, 
  Sparkle,
  Cpu
} from '@phosphor-icons/react';

const EVALUATOR_PRESETS = [
  {
    id: 'eval-rag',
    badge: 'RUBRIC 1 • GROUNDED RAG',
    title: 'Ask Grounded Growth Question',
    prompt: "How does Brian Chesky explain Airbnb's growth loops versus paid performance marketing?",
    description: "Evaluates multi-chunk vector retrieval, guest extraction, and precise transcript grounding with cosine threshold verification.",
    icon: TrendUp,
    accent: 'amber',
    mode: 'chat',
  },
  {
    id: 'eval-ship30',
    badge: 'RUBRIC 2 • SHIP 30 SKILL',
    title: 'Ship 30 for 30 Essay Generator',
    prompt: "Turn Lenny's interviews on Finding Product-Market Fit into a ~1,250-word Ship 30 for 30 essay.",
    description: "Generates an authentic Ship 30 essay with punchy hook, 3-5 modular frameworks, and a 48-hour tactical checklist.",
    icon: Feather,
    accent: 'amber',
    mode: 'ship30',
  },
  {
    id: 'eval-canvas',
    badge: 'RUBRIC 3 • CANVAS ARTIFACT',
    title: 'Generate Interactive Canvas Artifact',
    prompt: "Create an interactive HTML/JS churn & LTV sensitivity calculator widget.",
    description: "Emits a sandboxed HTML/JS artifact rendering inside an isolated, DOMPurified split-pane canvas drawer.",
    icon: CodeBlock,
    accent: 'amber',
    mode: 'chat',
  },
  {
    id: 'eval-refusal',
    badge: 'RUBRIC 4 • EPISTEMIC GUARDRAILS',
    title: 'Epistemic Guardrail Refusal',
    prompt: "How do I make chocolate chip cookies?",
    description: "Demonstrates strict refusal when a query lacks podcast transcript backing (< 0.65 similarity), preventing hallucination.",
    icon: ShieldWarning,
    accent: 'amber',
    mode: 'chat',
  },
];

export default function EmptyState({ onSelectPreset, mode }) {
  return (
    <div className="h-full flex flex-col items-center justify-center max-w-4xl mx-auto px-4 py-8 select-none">
      {/* Editorial Header */}
      <div className="text-center max-w-xl mx-auto mb-8">
        <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono text-[10px] uppercase tracking-wider mb-3">
          <Cpu size={12} weight="fill" />
          <span>Lenny Growth Intelligence Canvas</span>
        </div>
        <h2 className="text-xl md:text-2xl font-bold text-zinc-100 tracking-tight mb-2">
          {mode === 'ship30' ? 'Ship 30 for 30 Writing Engine' : 'High-Agency Growth Strategic Partner'}
        </h2>
        <p className="text-xs text-zinc-400 leading-relaxed">
          Select an evaluator benchmark card below to immediately test transcript grounding, the Ship 30 essay skill, interactive iframe artifacts, or strict epistemic refusals.
        </p>
      </div>

      {/* Asymmetric Evaluator Benchmark Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 w-full">
        {EVALUATOR_PRESETS.map((preset, idx) => {
          const Icon = preset.icon;
          return (
            <div
              key={preset.id}
              onClick={() => onSelectPreset(preset.prompt, preset.mode)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectPreset(preset.prompt, preset.mode);
                }
              }}
              className={`group relative p-4 rounded-xl bg-zinc-900/40 hover:bg-zinc-900/80 border border-zinc-800 hover:border-amber-500/40 transition-all duration-200 cursor-pointer flex flex-col justify-between text-left shadow-sm hover:shadow-amber-500/5 ${
                idx === 0 || idx === 3 ? 'md:col-span-1' : 'md:col-span-1'
              }`}
            >
              {/* Card Top Row */}
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="font-mono text-[10px] text-amber-400/90 font-medium tracking-wide">
                    {preset.badge}
                  </span>
                  <div className="w-6 h-6 rounded-lg bg-zinc-800 group-hover:bg-amber-500/20 border border-zinc-700/60 group-hover:border-amber-500/40 flex items-center justify-center text-zinc-400 group-hover:text-amber-300 transition-colors">
                    <Icon size={14} weight="bold" />
                  </div>
                </div>

                <h3 className="text-sm font-semibold text-zinc-200 group-hover:text-white transition-colors mb-1">
                  {preset.title}
                </h3>
                <p className="text-[11px] text-zinc-400 leading-relaxed mb-3">
                  {preset.description}
                </p>
              </div>

              {/* Prompt Trigger Banner */}
              <div className="mt-auto pt-2.5 border-t border-zinc-800/80 flex items-center justify-between gap-2">
                <span className="font-mono text-[11px] text-zinc-400 group-hover:text-amber-200/90 truncate transition-colors">
                  "{preset.prompt}"
                </span>
                <span className="flex-shrink-0 flex items-center gap-0.5 text-[10px] font-mono text-zinc-400 group-hover:text-amber-400 transition-colors">
                  <span>Run</span>
                  <ArrowUpRight size={10} weight="bold" />
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Subtext info */}
      <div className="mt-6 flex items-center gap-2 text-[10px] font-mono text-zinc-400">
        <Sparkle size={12} weight="fill" className="text-amber-400" />
        <span>Backed by PostgreSQL pgvector, strict cosine cutoff (&ge; 0.65), and dual-model runtime dispatch.</span>
      </div>
    </div>
  );
}

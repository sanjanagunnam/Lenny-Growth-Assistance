import React from 'react';
import { 
  Sparkle, 
  ChatTeardropText, 
  ArrowRight, 
  Code, 
  BookOpen, 
  Stack, 
  Cpu, 
  Database, 
  MagnifyingGlass, 
  GitBranch, 
  ShieldCheck, 
  FileCode, 
  Article, 
  Lightning, 
  CheckCircle,
  CaretDown,
  TrendUp,
  Sliders
} from '@phosphor-icons/react';

export default function LandingPage({ 
  onStartChat, 
  onSelectPrompt,
  health,
  backendUrl 
}) {
  const GUESTS = [
    {
      initials: 'BC',
      name: 'Brian Chesky',
      role: 'Co-Founder & CEO, Airbnb',
      topics: ['Founder Mode', 'Growth Loops vs Paid Ads', 'Unscalable Things'],
      gradient: 'from-rose-500 to-amber-500',
      shadow: 'shadow-rose-500/20',
      quote: "When COVID hit, we cut performance marketing and relied on our organic host-guest growth loop.",
      prompt: "How does Brian Chesky explain Airbnb's growth loops versus paid performance marketing?"
    },
    {
      initials: 'SD',
      name: 'Shreyas Doshi',
      role: 'Product Leader · Stripe, Twitter',
      topics: ['LNO Framework', 'High Agency', 'Pre-Mortems'],
      gradient: 'from-purple-500 to-indigo-500',
      shadow: 'shadow-purple-500/20',
      quote: "High agency is the refusal to accept the default world. High agency operators find a way.",
      prompt: "What is the LNO framework recommended by Shreyas Doshi on Lenny's Podcast?"
    },
    {
      initials: 'EV',
      name: 'Elena Verna',
      role: 'Growth Advisor · Miro, Amplitude',
      topics: ['PLG & Product-Led Growth', 'Freemium vs Trial', 'Self-Serve Funnels'],
      gradient: 'from-sky-500 to-cyan-400',
      shadow: 'shadow-sky-500/20',
      quote: "Product-led growth isn't a replacement for sales; it's a customer acquisition flywheel.",
      prompt: "How does Elena Verna distinguish product-led growth loops from traditional sales funnels?"
    },
    {
      initials: 'MC',
      name: 'Marty Cagan',
      role: 'Author of Inspired · SVPG Founder',
      topics: ['Product Discovery', 'Empowered Teams', '4 Big Product Risks'],
      gradient: 'from-emerald-500 to-teal-400',
      shadow: 'shadow-emerald-500/20',
      quote: "Leadership is about empowering teams with problems to solve rather than features to build.",
      prompt: "What are Marty Cagan's 4 big product risks and how do empowered teams address them?"
    }
  ];

  const CAPABILITIES = [
    {
      title: 'Grounded RAG Q&A',
      desc: "Every answer is strictly sourced from Lenny's Podcast transcripts. No hallucinations — each response cites the exact speaker, episode, and relevance score.",
      icon: MagnifyingGlass,
      color: 'sky',
      badge: 'Zero Hallucination'
    },
    {
      title: 'Multi-Provider LLM Stack',
      desc: 'Connect to Groq LPUs (~500 tokens/sec), Google Gemini Flash, Claude Sonnet, OpenAI GPT-4o, or 100% offline local Ollama with seamless auto-fallback.',
      icon: Cpu,
      color: 'purple',
      badge: 'Multi-Model'
    },
    {
      title: 'Interactive HTML Canvas',
      desc: 'Generate interactive 1-page strategy canvases, ROI calculators, and prioritization matrices rendered safely inside an isolated sandboxed iframe viewer.',
      icon: FileCode,
      color: 'emerald',
      badge: 'Sandboxed UI'
    },
    {
      title: 'Ship 30 Essay Engine',
      desc: 'Transform complex product strategies into structured ~1,250-word viral essays with bold hooks, modular pillars, and 48-hour action checklists.',
      icon: Article,
      color: 'amber',
      badge: 'Ship 30 for 30'
    },
    {
      title: 'Epistemic Guardrails',
      desc: 'Automatic similarity threshold gating refuses out-of-domain questions (e.g. cookie recipes, selenium scripts) to maintain 100% domain integrity.',
      icon: ShieldCheck,
      color: 'rose',
      badge: 'Strict Refusal'
    },
    {
      title: 'Multi-Thread Sessions',
      desc: 'Full concurrent conversation management with client-side caching, background thinking states, and one-click export to Markdown or HTML.',
      icon: Stack,
      color: 'indigo',
      badge: 'Concurrent'
    }
  ];

  const TECH_STACK = [
    {
      category: 'Frontend',
      color: 'sky',
      items: [
        { name: 'Vite 6', role: 'Fast Build Tool' },
        { name: 'React 18', role: 'UI Architecture' },
        { name: 'Tailwind CSS 4', role: 'Design System' },
        { name: 'Phosphor Icons', role: 'Vector Iconography' },
        { name: 'DOMPurify', role: 'XSS Sanitization' }
      ]
    },
    {
      category: 'Backend API',
      color: 'emerald',
      items: [
        { name: 'FastAPI', role: 'High-Performance ASGI' },
        { name: 'Python 3.11+', role: 'Core Runtime' },
        { name: 'SQLAlchemy', role: 'Async ORM Engine' },
        { name: 'SQLite / Postgres', role: 'Hybrid Storage' },
        { name: 'Uvicorn', role: 'Production Server' }
      ]
    },
    {
      category: 'AI & RAG Pipeline',
      color: 'purple',
      items: [
        { name: 'Semantic Vectors', role: '768-dim Embeddings' },
        { name: 'BM25 Lexical', role: 'Sub-ms Hybrid Search' },
        { name: 'Epistemic Gate', role: 'Cosine Cutoff (0.65)' },
        { name: 'tiktoken', role: 'Token Budget Allocator' },
        { name: 'LangChain Splitters', role: 'Context Chunking' }
      ]
    },
    {
      category: 'LLM Providers',
      color: 'amber',
      items: [
        { name: 'Groq Cloud', role: 'Flagship LPU (~500 t/s)' },
        { name: 'Google Gemini', role: 'Gemini Flash Frontier' },
        { name: 'Anthropic', role: 'Claude Sonnet 3.5' },
        { name: 'OpenAI', role: 'GPT-4o Mini' },
        { name: 'Ollama', role: '100% Offline Local' }
      ]
    }
  ];

  const isBackendHealthy = health?.status === 'healthy';

  return (
    <div className="min-h-screen w-full bg-[#090d16] text-slate-100 selection:bg-sky-500/25 selection:text-white font-sans overflow-x-hidden">
      
      {/* Background Ambient Glows */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-[-10%] left-1/2 -translate-x-1/2 w-[900px] h-[500px] bg-gradient-to-b from-sky-600/12 via-indigo-600/10 to-transparent rounded-full blur-[120px]" />
        <div className="absolute top-[35%] left-[-10%] w-[600px] h-[600px] bg-purple-600/8 rounded-full blur-[140px]" />
        <div className="absolute top-[65%] right-[-10%] w-[600px] h-[600px] bg-amber-600/6 rounded-full blur-[140px]" />
      </div>

      <div className="relative z-10">

        {/* HERO SECTION */}
        <section className="relative pt-24 pb-20 px-5 sm:px-10 flex flex-col items-center justify-center text-center">
          <div className="max-w-4xl mx-auto">
            
            {/* Top Badge */}
            <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/25 text-sky-300 text-xs font-mono font-medium mb-8 shadow-lg shadow-sky-500/10">
              <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
              <span>Lenny's Podcast • Evidence-Grounded AI Growth Strategist</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-4xl sm:text-6xl lg:text-7xl font-black tracking-tight leading-[1.08] mb-6 text-white">
              Ask anything about <br />
              <span className="bg-gradient-to-r from-sky-400 via-indigo-300 to-amber-300 bg-clip-text text-transparent">
                Product & Growth Strategy
              </span>
            </h1>

            {/* Description */}
            <p className="text-base sm:text-lg text-slate-300 leading-relaxed max-w-2xl mx-auto mb-10 font-normal">
              An AI assistant grounded strictly in <strong className="text-white font-semibold">Lenny's Podcast transcripts</strong>. 
              Every answer is cited. Every insight is sourced. Powered by a <strong className="text-white font-semibold">multi-provider LLM stack</strong> with 
              zero-delay hybrid vector retrieval.
            </p>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
              <button
                onClick={onStartChat}
                className="w-full sm:w-auto flex items-center justify-center gap-3 px-8 py-3.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-600 hover:from-sky-500 hover:to-indigo-500 shadow-xl shadow-sky-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <ChatTeardropText size={18} weight="fill" />
                <span>Launch Assistant Workspace</span>
                <ArrowRight size={16} weight="bold" />
              </button>
              
              <a
                href={backendUrl ? `${backendUrl}/docs` : 'http://localhost:8000/docs'}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full sm:w-auto flex items-center justify-center gap-2.5 px-7 py-3.5 rounded-xl font-medium text-sm text-slate-300 bg-white/[0.05] border border-white/10 hover:bg-white/[0.1] hover:text-white hover:border-white/20 transition-all"
              >
                <Code size={18} />
                <span>FastAPI Swagger Docs</span>
              </a>
            </div>

            {/* Key Metric Bento Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mx-auto">
              <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-md text-center hover:border-sky-500/40 transition-colors">
                <div className="text-3xl font-black text-sky-400">4+</div>
                <div className="text-[11px] text-slate-400 font-mono mt-1">Full Transcripts</div>
              </div>
              <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-md text-center hover:border-indigo-500/40 transition-colors">
                <div className="text-3xl font-black text-indigo-400">24</div>
                <div className="text-[11px] text-slate-400 font-mono mt-1">Indexed Chunks</div>
              </div>
              <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-md text-center hover:border-emerald-500/40 transition-colors">
                <div className="text-3xl font-black text-emerald-400">5</div>
                <div className="text-[11px] text-slate-400 font-mono mt-1">LLM Providers</div>
              </div>
              <div className="p-4 rounded-2xl bg-white/[0.04] border border-white/10 backdrop-blur-md text-center hover:border-amber-500/40 transition-colors">
                <div className="text-3xl font-black text-amber-400">100%</div>
                <div className="text-[11px] text-slate-400 font-mono mt-1">Grounded Citations</div>
              </div>
            </div>

          </div>
        </section>

        {/* KNOWLEDGE BASE SECTION */}
        <section className="py-20 px-5 sm:px-10 border-t border-white/5">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono text-slate-400 mb-3">
                  <BookOpen size={14} />
                  <span>Curated Knowledge Corpus</span>
                </div>
                <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight">
                  World-Class Product Leaders
                </h2>
                <p className="text-slate-400 text-sm mt-1 max-w-xl">
                  Unabridged podcast interviews. Every recommendation maps directly to an exact guest quote and audio segment.
                </p>
              </div>

              <span className="text-xs font-mono text-slate-500">
                Click any leader card to ask instantly ↗
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {GUESTS.map((guest, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectPrompt(guest.prompt)}
                  className="group relative p-6 rounded-3xl bg-white/[0.03] border border-white/10 hover:bg-white/[0.06] hover:border-white/20 backdrop-blur-sm transition-all duration-300 hover:shadow-xl cursor-pointer flex flex-col justify-between"
                >
                  <div>
                    <div className={`w-12 h-12 rounded-2xl bg-gradient-to-tr ${guest.gradient} flex items-center justify-center text-white font-black text-sm mb-5 shadow-lg ${guest.shadow} group-hover:scale-110 transition-transform`}>
                      {guest.initials}
                    </div>
                    <h3 className="text-base font-bold text-white mb-0.5 group-hover:text-amber-300 transition-colors">
                      {guest.name}
                    </h3>
                    <p className="text-xs text-slate-400 mb-3 font-medium">
                      {guest.role}
                    </p>
                    <p className="text-[12px] text-slate-400 leading-relaxed italic mb-4 line-clamp-3">
                      "{guest.quote}"
                    </p>
                  </div>

                  <div>
                    <div className="flex flex-wrap gap-1.5 pt-3 border-t border-white/5">
                      {guest.topics.map((t, tidx) => (
                        <span key={tidx} className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-300 font-mono">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CAPABILITIES SECTION */}
        <section className="py-20 px-5 sm:px-10 bg-white/[0.01] border-t border-white/5">
          <div className="max-w-6xl mx-auto">
            <div className="text-center max-w-2xl mx-auto mb-14">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono text-slate-400 mb-3">
                <Sliders size={14} />
                <span>Architecture Capabilities</span>
              </div>
              <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight mb-3">
                What This Assistant Can Do
              </h2>
              <p className="text-slate-400 text-sm leading-relaxed">
                Autonomous intent classification routes questions into grounded citations, interactive visual artifacts, or long-form essays.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {CAPABILITIES.map((cap, idx) => {
                const IconComponent = cap.icon;
                return (
                  <div
                    key={idx}
                    className="p-6 rounded-3xl bg-white/[0.03] border border-white/10 hover:bg-white/[0.05] hover:border-white/20 transition-all duration-300 backdrop-blur-sm flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-5">
                        <div className="w-10 h-10 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-amber-400">
                          <IconComponent size={20} />
                        </div>
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-400">
                          {cap.badge}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-white mb-2">
                        {cap.title}
                      </h3>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        {cap.desc}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* 3-STAGE PIPELINE ARCHITECTURE */}
        <section className="py-20 px-5 sm:px-10 border-t border-white/5">
          <div className="max-w-6xl mx-auto">
            <div className="text-center max-w-2xl mx-auto mb-14">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono text-slate-400 mb-3">
                <GitBranch size={14} />
                <span>RAG Pipeline Mechanics</span>
              </div>
              <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight mb-3">
                How Grounded Synthesis Works
              </h2>
              <p className="text-slate-400 text-sm leading-relaxed">
                Every prompt goes through a 3-stage pipeline before reaching the LLM, ensuring zero hallucination.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="relative p-7 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-sm overflow-hidden">
                <div className="absolute top-2 right-3 text-7xl font-black text-white/[0.03] font-mono">01</div>
                <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/25 flex items-center justify-center text-sky-400 mb-6">
                  <MagnifyingGlass size={20} />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Semantic & BM25 Hybrid Retrieval</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Query is evaluated against pre-indexed transcript vector chunks. BM25 lexical ranker combined with cosine similarity retrieves relevant excerpts in &lt;1ms.
                </p>
              </div>

              <div className="relative p-7 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-sm overflow-hidden">
                <div className="absolute top-2 right-3 text-7xl font-black text-white/[0.03] font-mono">02</div>
                <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center text-indigo-400 mb-6">
                  <GitBranch size={20} />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Epistemic Threshold Gating</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Similarity threshold gate checks if excerpts exceed confidence cutoffs. If off-topic, it returns a deterministic refusal message rather than fabricating claims.
                </p>
              </div>

              <div className="relative p-7 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-sm overflow-hidden">
                <div className="absolute top-2 right-3 text-7xl font-black text-white/[0.03] font-mono">03</div>
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/25 flex items-center justify-center text-purple-400 mb-6">
                  <Sparkle size={20} weight="fill" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">Grounded Generation & Artifacts</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Synthesizes evidence-grounded insights citing guest names and episodes, optionally generating live interactive HTML/JS canvases or Ship 30 essays.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* FULL TECH STACK */}
        <section className="py-20 px-5 sm:px-10 bg-white/[0.01] border-t border-white/5">
          <div className="max-w-6xl mx-auto">
            <div className="text-center max-w-2xl mx-auto mb-14">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[11px] font-mono text-slate-400 mb-3">
                <Code size={14} />
                <span>Production Architecture</span>
              </div>
              <h2 className="text-2xl sm:text-4xl font-black text-white tracking-tight mb-3">
                Built With Modern Engineering
              </h2>
              <p className="text-slate-400 text-sm leading-relaxed">
                Full-stack production setup: typed ASGI backend, modular vector search, and responsive React frontend.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {TECH_STACK.map((col, idx) => (
                <div key={idx} className="p-6 rounded-3xl bg-white/[0.03] border border-white/10 backdrop-blur-sm">
                  <div className="text-xs font-bold text-white mb-4 pb-2 border-b border-white/10 flex items-center justify-between">
                    <span>{col.category}</span>
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                  </div>
                  <div className="space-y-3">
                    {col.items.map((item, iidx) => (
                      <div key={iidx} className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-200">{item.name}</span>
                        <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.5 rounded bg-white/5 border border-white/5">
                          {item.role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* BOTTOM CTA CALLOUT */}
        <section className="py-20 px-5 sm:px-10 border-t border-white/5">
          <div className="max-w-3xl mx-auto">
            <div className="relative p-10 sm:p-14 rounded-3xl overflow-hidden bg-gradient-to-br from-sky-900/30 via-indigo-950/40 to-purple-950/30 border border-sky-500/20 text-center shadow-2xl">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-tr from-sky-500 to-amber-500 p-0.5 shadow-lg shadow-sky-500/20 mb-6">
                <div className="w-full h-full bg-zinc-950 rounded-[14px] flex items-center justify-center text-amber-400">
                  <Sparkle size={26} weight="fill" />
                </div>
              </div>
              <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight mb-3">
                Ready to explore growth loops?
              </h2>
              <p className="text-slate-300 text-sm max-w-md mx-auto mb-8 leading-relaxed">
                Ask about viral retention, PLG pricing, unscalable PMF tactics, or generate a Ship 30 essay. 100% cited answers.
              </p>
              <button
                onClick={onStartChat}
                className="inline-flex items-center gap-2.5 px-8 py-3.5 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-600 hover:from-sky-500 hover:to-indigo-500 shadow-xl shadow-sky-600/30 transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <ChatTeardropText size={18} weight="fill" />
                <span>Open Assistant Canvas</span>
                <ArrowRight size={16} weight="bold" />
              </button>
              <p className="text-[11px] font-mono text-slate-500 mt-5">
                Backend Status: {isBackendHealthy ? '🟢 Connected & Verified' : '🟡 Offline / Standalone'}
              </p>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="border-t border-white/5 py-8 px-5 sm:px-10 text-center text-xs text-slate-500 font-mono">
          <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-300 font-medium">Lenny AI Growth Assistant v1.0</span>
              <span>•</span>
              <span>Evidence-Grounded Intelligence</span>
            </div>
            <div className="flex items-center gap-4">
              <button onClick={onStartChat} className="hover:text-slate-300 transition-colors">
                Chat Workspace
              </button>
              <span>•</span>
              <a
                href={backendUrl ? `${backendUrl}/docs` : 'http://localhost:8000/docs'}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-slate-300 transition-colors"
              >
                API Docs
              </a>
              <span>•</span>
              <a
                href="https://github.com/sanjanagunnam/Lenny-Growth-Assistance"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-slate-300 transition-colors"
              >
                GitHub Repository
              </a>
            </div>
          </div>
        </footer>

      </div>
    </div>
  );
}

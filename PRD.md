# Product Requirements Document (PRD)
## The Lenny Growth Assistant

**Version:** 1.0.0  
**Status:** Ready for Release (Stage 5)  
**Author:** Lead Forward Deployed Engineer  
**Target Audience:** Product Managers, Growth Leads, Founders, Startup Operators  

---

## 1. Executive Summary & Vision

Lenny’s Podcast features hundreds of hours of high-signal interviews with the world’s foremost tech operators (e.g., Brian Chesky, Shreyas Doshi, Elena Verna, Gustaf Alströmer). However, searching for actionable tactical guidance across hours of audio or unstructured transcripts is tedious and error-prone. Generic LLMs (ChatGPT, Claude) hallucinate quotes, invent non-existent frameworks, and offer generic startup platitudes.

**The Lenny Growth Assistant** is an elite, evidence-grounded AI product advisor and content engine. It connects directly to curated transcript vectors, enforces strict epistemic grounding (zero hallucinations), produces viral Ship 30 for 30 essays (~1,250 words), and emits interactive execution artifacts (checklists, calculators, growth models) into a split-screen Growth Canvas.

---

## 2. Target Personas & Jobs-to-be-Done (JTBD)

### 2.1 Primary Personas
1. **The Early-Stage Founder**:
   - *Goal*: Discover product-market fit, design defensible organic growth loops, and adopt effective operational practices without hiring expensive consultants.
   - *Pain Point*: Drowning in contradictory generic advice; needs exact case studies from founders who survived existential crises (e.g. Brian Chesky on Airbnb in 2020).
2. **The Senior / Staff Product Manager**:
   - *Goal*: Implement battle-tested prioritization and team alignment frameworks.
   - *Pain Point*: Team suffers from perfectionist burnout and low agency; needs frameworks like Shreyas Doshi’s LNO model to restructure engineering sprints.
3. **The Growth Lead & Content Creator**:
   - *Goal*: Synthesize complex growth models into skimmable, high-impact Ship 30 for 30 essays and actionable checklists.
   - *Pain Point*: Spending hours transcribing and restructuring podcasts into viral formats.

### 2.2 Core Jobs-to-be-Done
- **JTBD 1 (Tactical Grounded Q&A)**: "When I encounter a growth or management bottleneck, I want to query Lenny's Podcast transcripts for exact guest frameworks so that I can make high-agency decisions backed by proven precedent."
- **JTBD 2 (Content Engine / Ship 30)**: "When I have a grounded insight, I want to automatically transform it into a ~1,250-word Ship 30 for 30 essay with punchy hooks and structured pillars so that I can educate my team or build an audience."
- **JTBD 3 (Artifact Generation)**: "When I need a reusable asset, I want the assistant to emit a standalone, interactive checklist, matrix, or calculator that I can preview, copy, or export immediately."

---

## 3. Core Operational Success Metrics (SLAs)

| Metric | Target SLA | Measurement Method | Failure Mitigation |
|---|---|---|---|
| **Retrieval Faithfulness** | **> 85%** | Percentage of claims cited directly from retrieved transcript chunks | Strict epistemic cutoff (`similarity >= 0.65`); return standard refusal if context is missing |
| **Local Response Latency** | **< 12.0s** | P95 time-to-first-token & generation on 8-core CPU / 16GB RAM | 15-second graceful timeout on Ollama with clean JSON fallback |
| **Zero-Trust Security Score** | **100% Pass** | Automated DOMPurify sanitization & iframe sandbox isolation tests | Restrict iframe with `sandbox="allow-scripts"`, block parent DOM/cookie access |
| **System Availability** | **99.9%** | Uptime of containerized `/healthz` endpoints | Exponential backoff retry on database and daemon connections |

---

## 4. Scope Choices & Strategic Trade-Offs

### 4.1 In Scope (Delivered in Stages 1–5)
- **Vector Database**: PostgreSQL 16 + `pgvector` with IVFFlat cosine similarity indexing.
- **Dual-Model Support**: Local Ollama (`llama3.2` + `nomic-embed-text`) with cloud Anthropic Claude 3.5 Sonnet fallback.
- **Session Persistence**: Full thread storage in PostgreSQL with timestamps, roles, and artifact metadata.
- **Epistemic Refusal Gate**: Immediate standard refusal (`"The available podcast transcripts do not cover this specific question."`) if similarity is `< 0.65`.
- **Ship 30 for 30 Writing Engine**: Generation of structured, ~1,250-word essays with punchy hooks and bold anchor sentences.
- **Split-View Canvas**: Slide-out artifact drawer with Preview (HTML/Markdown) and Raw Code views.
- **One-Command Deployment**: 4-tier Docker Compose topology (`db`, `ollama`, `backend`, `frontend`).

### 4.2 Out of Scope (Intentional Trade-Offs)
- **Audio Voice Synthesis**: Audio generation is excluded to prevent local container bloat and GPU memory exhaustion.
- **Live Internet Scraping**: The assistant refuses to browse external sites; advice is strictly confined to curated Lenny Podcast transcripts.
- **Multi-Tenant User Auth (SSO)**: Local development and single-operator environments do not require OAuth/JWT friction.

---

## 5. Failure Modes & Mitigations

1. **Hallucination on Uncovered Topics**:
   - *Risk*: Model extrapolates advice on cooking, crypto trading, or general coding.
   - *Mitigation*: Epistemic similarity gate blocks queries with cosine similarity `< 0.65` and forces exact refusal string.
2. **Local Daemon Starvation / High Latency**:
   - *Risk*: Ollama hangs or consumes 100% CPU on low-end hardware.
   - *Mitigation*: 15-second strict timeout on backend calls; returns clean HTTP 504 with an actionable suggestion to switch to Anthropic.
3. **Malicious HTML Artifact Injection (XSS)**:
   - *Risk*: Generated HTML attempts parent window redirect or cookie theft.
   - *Mitigation*: All HTML passes through `DOMPurify` and renders in an `<iframe>` configured with `sandbox="allow-scripts"`, omitting `allow-same-origin`.
4. **Database Startup Latency**:
   - *Risk*: Backend starts before PostgreSQL container is ready to accept connections.
   - *Mitigation*: Docker Compose `depends_on: { db: { condition: service_healthy } }` combined with exponential backoff retry in Python code.

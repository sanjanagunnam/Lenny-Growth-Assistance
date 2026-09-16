# Design System & Aesthetic Directives
## The Lenny Growth Assistant

**Version:** 1.0.0  
**Role:** Staff Design Engineer  
**Taste-Skill v2.0 Calibration:** `DESIGN_VARIANCE: 8` | `MOTION_INTENSITY: 5` | `VISUAL_DENSITY: 6`  

---

## 1. Design Direction & Aesthetic Rationale

> **Design Read**: Growth Operator Canvas for Product Managers and Growth Engineers, with an editorial yet high-density aesthetic, leaning toward Linear/Vercel-inspired monochrome with high-contrast amber telemetry accents.

### Anti-Generic AI Principles
- **No Purple Gradient Meshes**: Standard AI templates rely on generic indigo-purple gradients that feel like commodity wrapper apps. We enforce a purposeful, obsidian-monochrome foundation.
- **No Icon Defaults**: Lucide icons are strictly banned. The design system uses exclusively `@phosphor-icons/react` with refined geometric weights.
- **No Uncalibrated Glassmorphism**: Blurs are restrained to functional overlays (navbar and modal backdrops) with explicit solid fallbacks.
- **No Three Identical Cards**: Grids feature visual hierarchy, distinct card treatments, and varied typography scales.

---

## 2. Color Tokens & Palette Calibration

| Token | Hex Code | Purpose |
|---|---|---|
| `bg-primary` | `#09090B` (Zinc-950) | Base canvas background; deep obsidian surface |
| `surface-1` | `#18181B` (Zinc-900) | Secondary surface: cards, input containers, active items |
| `border-subtle` | `#27272A` (Zinc-800) | Structural dividers, component borders, and gutters |
| `border-accent` | `#3F3F46` (Zinc-700) | Hover outlines, interactive states |
| `text-primary` | `#F4F4F5` (Zinc-100) | Primary headers, conversational prompts, titles |
| `text-muted` | `#A1A1AA` (Zinc-400) | Secondary descriptions, timestamps, helper text |
| `accent-amber` | `#F59E0B` (Amber-500) | Telemetry accent: model badges, citations, Ship 30 mode |
| `accent-emerald` | `#10B981` (Emerald-500) | Database and vector healthy status indicators |

---

## 3. Typography & Information Hierarchy

- **Primary Interface Typeface**: `Inter` (sans-serif)
  - Clean, legible geometric grotesque optimized for high-density UI and long-form conversational reading.
- **Telemetry & Monospace Typeface**: `JetBrains Mono`
  - Applied to model identifiers (`llama3.2`, `claude-3-5-sonnet`), similarity match percentages (`88% match`), source filenames, and token statistics.
- **Type Scales**:
  - `h1 / Title`: 14px / 16px, font-semibold (compact executive density)
  - `Body / Chat`: 12px / 13px, line-height 1.65 (comfortable reading rhythm)
  - `Captions & Metadata`: 10px / 11px font-mono (precise telemetry badges)

---

## 4. Information Architecture & Dual-Pane Canvas

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ NAVBAR: Lenny Growth Assistant [v1.0] | Mode: [PM Chat / Ship 30] | Health  │
├──────────────┬───────────────────────────────┬──────────────────────────────┤
│ SIDEBAR      │ CHAT STREAM                   │ GROWTH CANVAS / ARTIFACT     │
│              │                               │                              │
│ + New Thread │ [User Message Bubble]         │ Tab: [Preview] | [Raw Code]  │
│              │                               │                              │
│ Sessions:    │ [Assistant Answer Bubble]     │ [Rendered Artifact Sandbox]  │
│ • Airbnb PM  │ ┌───────────────────────────┐ │  - Interactive Calculators   │
│ • LNO Model  │ │ Grounded Citations (2)    │ │  - Markdown Checklists       │
│ • Pricing    │ └───────────────────────────┘ │  - Strategic Playbooks       │
│              │                               │                              │
│              │ [Open in Canvas Button ───►]  │ [Copy] [Download] [Close]    │
│              ├───────────────────────────────┤                              │
│              │ INPUT: [ Ask a question... ]  │                              │
└──────────────┴───────────────────────────────┴──────────────────────────────┘
```

### Layout Stability
- **`min-h-[100dvh]`**: The entire application container enforces dynamic viewport units (`min-h-[100dvh] h-[100dvh]`) to eliminate the mobile URL bar collapsing issue inherent to `h-screen`.
- **Slide-Out Dual Pane**: The Growth Canvas operates side-by-side on desktop (>1024px) taking 50% width, or as a full overlay on mobile, smoothly animating without resizing or reflowing the conversation stream.

---

## 5. Micro-Interactions & Motion Budget

- **Motion Intensity (5/10)**: Purposeful, functional transitions (200ms ease-in-out) on drawers, tooltips, and tab changes.
- **Copy Feedback**: One-click copy buttons transition from clipboard icon to checkmark with an emerald pulse for 2,000ms.
- **Active Canvas Ping**: When an assistant response produces an artifact, a subtle amber pulse indicator notifies the user to inspect the Growth Canvas.

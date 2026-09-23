# Design system (original; distilled from the reference analysis of Attio, Linear, V7 Go, incident.io, Granola)

Conclusion of the analysis: Attio's shell (sidebar + toolbar + table + beside-panel), Linear's interaction contract (suggestion attached to the field it changes, inspect → accept/decline, reasoning on demand, background processing state), V7's evidence model (click a value → highlight the source, page/reference + snippet + confidence), incident.io's journey header (lifecycle stepper, severity/owner/status, human vs agent timeline), Granola's typography and restraint (one dominant working document, reading width). Density between Attio and Granola: 14px base in lists, 15–16px in the working document.

## B1 Principles
1. The work is the hero. The centre workspace gets the most contrast, size and motion budget. Chrome is quiet.
2. Every agent claim is inspectable. No finding without an evidence affordance.
3. State is never ambiguous. Proposed / Applying / Applied / Verified differ by colour **and** icon **and** text.
4. Motion explains, never decorates. Every animation maps to a state change or a spatial relationship.
5. Projector-safe. ≥ 4.5:1 for all text, 3:1 for UI boundaries, 15px minimum body in the working area.

## B2 Colour tokens (light, default)
| Token | Value | Use |
|---|---|---|
| `--bg-app` | `#F5F6F8` | App background behind panels |
| `--bg-surface` | `#FFFFFF` | Panels, cards, table |
| `--bg-surface-2` | `#F9FAFB` | Table header, secondary panels, hover rows |
| `--bg-inset` | `#F1F3F5` | Inputs, code/tool-log background |
| `--border` | `#E4E7EB` | Default hairline |
| `--border-strong` | `#CDD2D8` | Focused/selected outline |
| `--text-primary` | `#16181D` | Headlines, values |
| `--text-secondary` | `#565B66` | Labels, descriptions (7.2:1) |
| `--text-tertiary` | `#7C8290` | Meta, timestamps (4.6:1) |
| `--text-inverse` | `#FFFFFF` | On accent/dark |
| `--accent` | `#2457E6` | Primary buttons, links, selected state, focus ring |
| `--accent-hover` | `#1C48C4` | |
| `--accent-active` | `#163A9E` | |
| `--accent-soft` | `#E8EEFF` | Selected row bg, proposed-change tint |
| `--accent-soft-border` | `#B9C8FA` | Border of proposed-change highlight |

Status (always tinted bg + dark fg + icon + text; solid fills only for the single primary button):

| State | Fg | Bg | Border | Icon |
|---|---|---|---|---|
| Proposed | `#2457E6` | `#E8EEFF` | `#B9C8FA` | ◇ dashed diamond |
| Applying | `#7A4B00` | `#FFF4DD` | `#F5D48A` | ◌ spinner |
| Applied | `#1F5A8E` | `#E4F1FB` | `#A9CDEB` | ● solid dot |
| Verified | `#166534` | `#E6F6EC` | `#9FD6B2` | ✓ check |
| Attention | `#8A4B00` | `#FFF3E0` | `#F3C98B` | ! triangle |
| Failed | `#9F1D1D` | `#FDEAEA` | `#F0A8A8` | ✕ |
| Neutral / Info | `#565B66` | `#F1F3F5` | `#D9DEE5` | ○ |

Evidence & diff: `--evidence-hl #FFE68A @45%`, `--evidence-hl-border #D9A400`, `--diff-removed-bg #FDEAEA`, `--diff-added-bg #E6F6EC`, `--diff-changed-bg #E8EEFF`.

Dark theme (behind `data-theme="dark"`, optional): `--bg-app #0F1115`, `--bg-surface #171A20`, `--bg-surface-2 #1D2129`, `--border #2A2F39`, `--text-primary #EEF0F4`, `--text-secondary #A6ACB8`, `--accent #5B8CFF`, `--accent-soft #1B2A4F`. Status: lighten fg ~25%, darken bg to a 12–15% tint. Keep icons.

## B3 Typography
| Token | Size / LH / Weight | Use |
|---|---|---|
| `--t-display` | 28 / 34 / 600, tracking −0.01em | Case title in header |
| `--t-h1` | 22 / 28 / 600 | Panel titles |
| `--t-h2` | 17 / 24 / 600 | Section titles inside panels |
| `--t-body-lg` | 16 / 26 / 400 | Working document, evidence text |
| `--t-body` | 14 / 20 / 400 | Lists, table cells, agent panel |
| `--t-label` | 12 / 16 / 500, tracking +0.04em (uppercase optional) | Field labels, eyebrows |
| `--t-meta` | 12 / 16 / 400 | Timestamps, IDs |
| `--t-mono` | 13 / 20 / 400 monospace | Tool names, IDs, event details |

Family: Inter (or Geist) + one mono (JetBrains Mono / ui-monospace). `font-variant-numeric: tabular-nums` in every table and metric.

## B4 Spacing, radius, elevation, motion
- Spacing: 4 · 8 · 12 · 16 · 20 · 24 · 32 · 40 · 48 · 64.
- Radius: `--r-sm 6px` (chips, inputs) · `--r-md 10px` (cards, rows) · `--r-lg 14px` (panels, drawers) · `--r-full`.
- Elevation: `--e-0` none (borders do the work) · `--e-1 0 1px 2px rgba(16,24,40,.06)` · `--e-2 0 8px 24px rgba(16,24,40,.10)` · `--e-3 0 24px 48px rgba(16,24,40,.16)`.
- Durations: `--d-fast 120ms` · `--d-base 200ms` · `--d-slow 320ms` · `--d-reveal 480ms`.
- Easings: `--ease-out cubic-bezier(.2,.8,.2,1)` · `--ease-in cubic-bezier(.4,0,1,1)` · `--ease-inout cubic-bezier(.65,0,.35,1)`.
- `prefers-reduced-motion: reduce` → durations 0 except opacity fades ≤120ms; no translate/scale.

## B5 Screen layout (desktop 1440)
```
┌──────────────────────────────────────────────────────────────────────────┐
│ Top bar 48px: [Logo] [Workspace ▾]      [⌘K Search…]      [Status ●] [⋯]  │
├──────────┬────────────────────────────────────────────┬──────────────────┤
│ LEFT     │ CENTER                                     │ RIGHT            │
│ 240px    │ flexible (min 640px)                       │ 340px            │
│          │ ┌ Case header 72px ────────────────────┐   │ ┌ Agent panel ─┐ │
│ Cases    │ │ Title · severity · owner · status ·  │   │ │ Activity     │ │
│ Search   │ │ journey stepper                       │   │ │ Findings     │ │
│ Filters  │ └───────────────────────────────────────┘   │ │ Evidence     │ │
│ Status   │ ┌ Workspace (replaceable) ─────────────┐   │ │ Proposal     │ │
│ groups   │ │ board / document / table with        │   │ │ Apply CTA    │ │
│          │ │ proposed-change overlays             │   │ └──────────────┘ │
│          │ └──────────────────────────────────────┘   │ (collapsible →   │
│          │                                            │  48px rail)      │
└──────────┴────────────────────────────────────────────┴──────────────────┘
```
- Left 240px: 16px padding, search 36px, filter chips, grouped list "Needs attention / In progress / Verified". Row 44px: status icon 16px + title 14/500 one-line ellipsis + meta 12px. Selected: `--accent-soft` bg + 2px `--accent` left bar. Collapses to a 56px icon rail < 1180px.
- Centre: case header 72px (title `--t-display`, chip row 28px: severity, owner, status; journey stepper Detected → Triaged → Proposed → Applied → Verified as 6px dots + labels, current in accent). Workspace below: 24px padding, `--bg-surface`, `--r-lg`. Proposed changes render **on the workspace itself**, never only in the right panel.
- Right 340px: header 44px "Agent" + collapse. Sections: Activity → Findings → Evidence → Proposal summary → Apply panel (sticky bottom 72px). Collapse to 48px rail with 3 icons; centre expands `--ease-inout 320ms`.
- Breakpoints: ≥1440 three columns · 1180–1439 left rail 56px, right 320px · 900–1179 right panel becomes an overlay drawer · <900 single column (functional, not polished).

## B6 Components (with states)
- **Case list row**: default · hover `--bg-surface-2` · selected · focus ring 2px accent 2px offset · unread (600 + 6px dot) · loading skeleton (3 rows, shimmer 1.4s).
- **Case header**: title · severity chip · owner · status chip · stepper · overflow. Stepper: current dot scales 1 → 1.25 → 1 (240ms) on step completion; connector fills left→right 320ms.
- **Agent activity panel**: each step = 20px status icon column + label 14/500 + optional detail line 12px grey + timestamp right. Step states: pending (hollow circle, tertiary) · running (16px spinner, primary text, faint shimmer) · done (check, secondary) · failed (✕ red + "Retry"). Plain-language label comes from the backend event map; technical detail sits in a "Details" disclosure that expands to a `--t-mono` block on `--bg-inset` with tool name, argument summary, duration. Determinate bar only when a total is known; otherwise "3 of 5".
- **Findings list**: card icon + one-line claim 14/500 + "Evidence (2)" link + relevance chip. Hover raises `--e-1`. Click opens the evidence drawer and triggers the linked highlight in the workspace.
- **Evidence drawer**: stacked view inside the right panel (slides in 200ms). Shows the cited record/rule with the passage highlighted (`--evidence-hl`, 2px `--evidence-hl-border`), reference id, snippet, confidence as text High/Medium/Low + 3-segment bar. Actions: Mark verified · Flag · Copy reference.
- **Proposed-change comparison**: row = field label · old value (strikethrough, `--diff-removed-bg`) · arrow · new value (`--diff-added-bg`) · constraint checks (✓ Capacity ✓ Deadline ! Overlap) · "Why" link. Grouped by affected object. Bulk "Apply all" + per-row "Skip" (optional).
- **Validation results**: list of checks with pass/warn/fail icon + text. Any fail disables Apply and explains what to change. Warn allows Apply with an explicit acknowledgement checkbox.
- **Apply panel** (sticky bottom of right panel): summary line "3 changes · 2 checks passed · 1 warning". Primary `--accent` "Apply proposal" → "Applying…" (spinner, disabled) → "Applied" (blue) → "Verified" (green, check) only after the backend verification event. Secondary "Request revision". **Never optimistic.**
- **Empty / loading / missing-info / failed / success**: empty = 40px icon + one sentence + one action, no illustrations. Loading = skeletons matching the final layout. Missing information = amber card at top of workspace listing missing fields as inline inputs + "Continue" that re-runs the agent; user input preserved on any error. Failed = red card with plain reason, "Retry" and "Show details" (mono log). Verified = green banner in workspace + header chip Verified + stepper complete; banner collapses after 6s to a compact chip.

## B7 Animation spec
| ID | Trigger | Animation | Timing |
|---|---|---|---|
| M1 | Select case | Centre crossfade opacity 0→1, translateY 6→0 | 200ms out |
| M2 | Panel collapse/expand | Width tween; content fades at 60% | 320ms in-out |
| M3 | Agent step starts | Icon hollow→spinner; label tertiary→primary | 120ms |
| M4 | Agent step done | Spinner → check, scale 0.6→1 | 200ms out |
| M5 | Streamed agent text | Reveal by word, no cursor flicker | 30ms/word |
| M6 | Proposal arrives | Changed rows get `--diff-changed-bg`, fade 0→1 with 60ms stagger; 1px accent outline pulses once | 320ms + 600ms |
| M7 | Hover a change | Related finding gets `--accent-soft` bg | 120ms |
| M8 | Click finding | Workspace scrolls/pans to element, outline draws in; evidence drawer slides in | 400ms + 200ms |
| M9 | Open source split | Centre 100 → 55/45; highlight box draws (stroke-dashoffset) | 320ms + 300ms |
| M10 | Apply click | Button label swap 80ms fade; rows switch to "applying" hatch at 30% | 120ms |
| M11 | Applied event | Rows tint `--diff-added-bg`, settle with an "Applied" chip | 200ms |
| M12 | Verified event | Header chip tween to Verified, stepper last dot pulse, green banner slides down | 240ms |
| M13 | Failure | Card slides in from top 8px; offending row shakes 2px×2 (skip if reduced motion) | 200ms |
| M14 | Skeleton | Linear shimmer 1.4s `--bg-inset` → `--bg-surface-2` | — |
| M15 | Constraint change | Only updates a "Recompute" button badge; **no auto-calls** | 120ms |

No bounce/overshoot; nothing loops except spinner, shimmer and single-pulse outlines; max two things animate at once; every transition ≤ 480ms.

## B8 Event → label map (the backend sends labels; the UI must not invent them)
`get_case` → Reading the case · `find_resources` → Checking available workers · `lookup_rules` → Looking up the rules · `simulate_plan` → Simulating the plan · `proposal.validate` → Checking deadlines and capacity · `proposal.apply` → Applying changes · `state.verify` → Confirming the changes were saved · `agent.error` → Something went wrong.

## B9 State machine (visual contract)
```
Idle ─▶ Analyzing ─▶ Proposed ─▶ Applying ─▶ Applied ─▶ Verified
                 ├▶ NeedsInfo ─▶ (new run)         └▶ Failed
                 ├▶ Infeasible
                 └▶ Failed
```
| State | Header chip | Workspace | Right panel CTA |
|---|---|---|---|
| Idle | Neutral "New" | Plain data | "Run analysis" |
| Analyzing | Amber "Analyzing" | Plain data + subtle top progress line | disabled |
| NeedsInfo | Amber "Needs information" | Missing-info card | "Continue" |
| Infeasible | Red-amber "Infeasible" | Blocking constraints card | "Adjust inputs" |
| Proposed | Blue "Proposed" | Highlighted changes | "Apply proposal" |
| Applying | Amber "Applying" | Hatched changes | "Applying…" disabled |
| Applied | Blue "Applied" | Changes settled + chips | "Verifying…" |
| Verified | Green "Verified" | Green banner | "Done" |
| Failed | Red "Failed" | Error card | "Retry" |

## B10 Accessibility & presentation
All text ≥ 4.5:1. Body ≥ 15px in workspace, 14px elsewhere, nothing below 12px. Keyboard: ↑/↓ case list, Enter open, ⌘K search, E evidence, A apply (with confirmation), Esc closes drawers. Focus ring 2px accent 2px offset, never removed. Colour is never the only channel. Explanations are click-to-open, not hover-only. `aria-live="polite"` for agent step completion and state changes.

## B11 Build order
1. Tokens as CSS variables + Tailwind theme; light first, dark behind `data-theme`.
2. Shell: top bar, left list, centre frame, right panel with collapse.
3. Case header + journey stepper + status chips.
4. Agent activity panel with event map and disclosure.
5. Workspace slot with a `ResultType → Component` registry; ship the board first.
6. Proposed-change overlay + comparison list + validation.
7. Evidence drawer + linked highlight.
8. Apply panel wired to real events, state machine.
9. All five non-happy states.
10. Motion pass last, behind the reduced-motion guard.

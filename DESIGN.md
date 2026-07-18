---
name: InteliAI
description: Enterprise AI knowledge platform — grounded answers, traceable to source.
colors:
  bg: "#f1e9e2"
  surface: "#faf6f2"
  surface-raised: "#e9ded3"
  border: "#d9c9b8"
  ink: "#2b2118"
  ink-muted: "#6b5d52"
  accent: "#a9613f"
  success: "#4f7a4a"
  warning: "#9c6b1f"
  critical: "#a4402f"
typography:
  display:
    fontFamily: "Inter Tight, Inter, -apple-system, sans-serif"
    fontSize: "clamp(1.75rem, 2.5vw, 2.5rem)"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter Tight, Inter, -apple-system, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter, -apple-system, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, -apple-system, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.01em"
  mono:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
rounded:
  sm: "6px"
  md: "10px"
  lg: "14px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "32px"
  xl: "56px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#faf6f2"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-primary-hover:
    backgroundColor: "#8f4e32"
    textColor: "#faf6f2"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "10px 18px"
---

# Design System: InteliAI

## 1. Overview

**Creative North Star: "The Terminal for Trust"**

InteliAI is not a SaaS metrics dashboard wearing an AI badge — it is a workspace where the act of asking a question and the act of verifying the answer are the same motion. The system takes its discipline from Linear's density and restraint, Vercel's typographic confidence, and Bloomberg Terminal's refusal to decorate, but expressed in a warm, paper-and-ink light register rather than a dark cockpit — this is a document workspace for people making judgment calls, not a control room. Every screen exists to answer one question fast and let the user check the work without leaving the page.

This system explicitly rejects: bright gradient hero-metric cards, glassmorphism as decoration, identical icon-heading-text card grids, purple "AI" clichés, rainbow status coloring, and uniform entrance animation applied to everything regardless of what it reveals. It also rejects looking like a generic analytics dashboard — stat tiles are a supporting player here, never the hero.

**Key Characteristics:**
- Warm nude/paper neutrals carry the interface; color is earned, not decorative
- One accent (clay/terracotta) reserved for AI-in-progress and primary actions only
- Citations and source text are first-class, not a collapsed afterthought
- Motion reports state (streaming, indexing, verifying) — it doesn't perform brand

## 2. Colors

Warm nude neutrals — paper, sand, clay — carry the interface; a single terracotta accent marks AI activity and primary actions; three status colors are reserved strictly for outcome, never decoration.

### Primary
- **Clay** (#a9613f): the *only* accent color in the system. Used for the primary button, active nav item, the AI "thinking/streaming" indicator, and focus rings. Nowhere else.

### Neutral
- **Sand** (#f1e9e2): app background. Warm nude, not pure white — the base of the paper-and-ink register.
- **Paper** (#faf6f2): the base surface for sidebars, cards, and input bars — lighter than Sand, reads as a sheet laid on the desk.
- **Paper Raised** (#e9ded3): hover/active surface state, and any panel that sits above another panel (dropdowns, modals).
- **Rule** (#d9c9b8): all borders and dividers. Never louder than this.
- **Ink** (#2b2118): primary text. Near-black espresso, not pure black — softer against the warm neutrals.
- **Ink Muted** (#6b5d52): secondary text, timestamps, metadata labels. Verified ≥4.5:1 against Sand and Paper.

### Status (reserved — outcome only, never décor)
- **Verified Moss** (#4f7a4a): successful retrieval, verified citation, healthy status. Never used for generic "success" toasts unrelated to retrieval/verification.
- **Caution Ochre** (#9c6b1f): degraded state, unverified claim, partial coverage.
- **Critical Brick** (#a4402f): failed retrieval, failed job, system-down. Reserved for genuine failure states, not form validation nitpicks. Kept visually distinct from Clay (redder, less orange) so accent and error are never confused.

### Named Rules
**The One Accent Rule.** Clay appears on the primary CTA, the active nav item, and live AI state indicators — nowhere else. If you reach for clay on a fourth kind of element, stop; it isn't earning its rarity.

**The Status-Means-Something Rule.** Moss/ochre/brick only ever describe retrieval, verification, or system health outcomes. They never double as generic UI accents (no green "success" toast for a settings save — use neutral ink for that).

## 3. Typography

**Display Font:** Inter Tight — a tighter-tracked cut used only for page titles and section headlines, giving headlines the compressed, confident set of Apple.com's SF Pro Display without adopting a licensed system font.
**Body / UI Font:** Inter — every paragraph, button, nav item, and label. Same type family as Inter Tight, different cut, so headline and body still feel like one voice, not two unrelated fonts.
**Data / Citation Font:** IBM Plex Mono — reserved for chunk text, citation metadata (page/section/clause refs), audit-log rows, and diagnostic values. This is the one place a second, distinctly technical voice is deliberate: it marks "this is retrieved source data," not authored UI copy.

**Character:** Three fonts, three jobs — a tight display cut for headlines (Apple's compressed confidence), a warm workhorse sans for everything a human wrote, and a monospace for everything the system retrieved verbatim. No serif, no script, no fourth family.

### Hierarchy
- **Display** (Inter Tight, 600, `clamp(1.75rem, 2.5vw, 2.5rem)`, 1.15, -0.02em): page titles only — one per page, never repeated in a card below it.
- **Title** (Inter Tight, 600, 1.125rem, 1.3, -0.01em): section headers, card titles, modal titles.
- **Body** (Inter, 400, 0.9375rem, 1.55): all prose, answers, UI copy. Capped at 70ch measure in the chat/citation column.
- **Label** (Inter, 500, 0.8125rem, 0.01em tracking): metadata, timestamps, nav items, table headers, badges. Never uppercase — uppercase labels are the 2023 AI-dashboard tell.
- **Mono** (IBM Plex Mono, 400, 0.8125rem, 1.5): retrieved chunk text inside the Citation Preview, audit event payloads, diagnostic key/value rows, document IDs.

### Named Rules
**The One Voice Rule.** Every UI weight step is 600→500→400 in Inter/Inter Tight; nothing in between. If two elements feel like they need different intermediate weights, one of them is miscategorized.

**The Verbatim-Gets-Mono Rule.** IBM Plex Mono marks text the system retrieved or logged, never text a person composed. If it wasn't pulled from a document, a job record, or an audit event, it isn't mono.

## 4. Elevation

Flat by default; depth comes from the neutral ramp (Sand → Paper → Paper Raised), not shadows. A single soft ambient shadow marks anything that floats above the page flow (dropdowns, modals, the citation preview popover) — never used on static cards sitting in the normal document flow.

### Shadow Vocabulary
- **Float** (`box-shadow: 0 12px 28px rgba(43,33,24,0.16)`): dropdowns, modals, popovers — anything overlaying content below it. Warm-tinted shadow (from Ink, not pure black) so it doesn't read as a cold UI-kit default on a nude background.

### Named Rules
**The Flat-at-Rest Rule.** Cards, panels, and list rows carry zero shadow at rest. Shadow appears only on elements that literally float above the page (portal-rendered), never as ambient card polish.

## 5. Components

### Buttons
- **Shape:** 6px radius (`{rounded.sm}`) — slightly rounded, never pill-shaped, never square.
- **Primary:** Clay background, Paper text (light text on the saturated accent, standard contrast direction for a light UI), 10px/18px padding.
- **Hover / Focus:** primary deepens to #8f4e32; focus-visible gets a 2px clay ring offset 2px, never a glow/blur.
- **Secondary:** Paper Raised background, Ink text, Rule border — used for every non-primary action; there is no tertiary/ghost variant beyond this to avoid button-hierarchy sprawl.

### Cards / Containers
- **Corner Style:** 10px radius (`{rounded.md}`).
- **Background:** Paper; Paper Raised only on hover when the whole card is a click target.
- **Shadow Strategy:** none (see Elevation) — separation comes from the Rule border only.
- **Border:** 1px Rule, full border on all four sides. Never a colored left/right stripe.
- **Internal Padding:** 20px (`{spacing.md}`) standard; 32px for hero/summary cards.

### Inputs / Fields
- **Style:** Paper background, 1px Rule border, 6px radius.
- **Focus:** border shifts to Clay, no glow.
- **Error:** border shifts to Critical Brick plus a one-line message below, not a filled field.

### Navigation
- **Style:** fixed left rail, Sand background (same as page, not a separate panel — no gradient sidebar). Label-weight items, Ink Muted at rest, Ink + Clay left-edge indicator (2px, the one place a "stripe" is intentional: an active-state marker, not a decorative border) on the active route.
- **Mobile:** collapses to a bottom-anchored icon bar, not a hamburger-overlay — enterprise users on tablets need one-tap access to Ask/Documents/Audit, not a hidden drawer.

### Citation Preview (signature component)
The trust mechanism of the product. Renders inline in the chat/document flow (not a modal): a bordered Paper-Raised block that expands from the citation chip with a single 120ms height transition, showing the exact chunk text **in Mono** with the matched span highlighted in a 15%-opacity Clay wash, plus its regulation/section/page metadata as Label-weight text along the top edge.

## 6. Do's and Don'ts

### Do:
- **Do** keep the base warm and near-monochrome; let Clay (#a9613f) be the only saturated color a user sees in a normal session.
- **Do** show the retrieval/verification path for every answer — citations are structural, not a collapsed footnote.
- **Do** use motion only to report real state: streaming tokens, a job moving from queued → indexing → ready, a panel expanding. Reduced-motion users get an instant crossfade equivalent for every transition.
- **Do** hold body text to Ink or Ink Muted only — both independently verified ≥4.5:1 against Sand and Paper.

### Don't:
- **Don't** use gradient backgrounds or gradient text anywhere.
- **Don't** use glassmorphism/backdrop-blur as decoration (the current `backdrop-blur` + translucent cards go).
- **Don't** build identical icon+heading+text card grids as a default layout move.
- **Don't** use border-left/border-right color stripes as a decorative accent (the one exception is the 2px active-nav-item marker, which is a state indicator, not decoration).
- **Don't** apply a uniform framer-motion fade/slide to every card, row, and header on page load — this is the single strongest "AI generated this" tell in the current build and must be removed wholesale, not tuned.
- **Don't** show fake/hardcoded data: no static progress-bar widths, no hardcoded footer build/copyright strings, no "Coming soon" dead-end buttons shipped as if finished.
- **Don't** revert to a dark theme. This system is light/nude by explicit direction — dark mode was tried and rejected.

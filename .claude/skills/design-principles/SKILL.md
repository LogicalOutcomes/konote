---
name: design-principles
description: Use when making aesthetic decisions for web interfaces - choosing design direction, color palettes, typography, spacing systems, visual hierarchy, or UI polish. Use when user asks to make something look nicer, improve UX, choose a style, or needs guidance on crafted interface design. NOT for writing implementation code (use frontend-design for that).
---

# Design Principles

Precise, crafted design for enterprise software, SaaS dashboards, admin interfaces, and web applications. Jony Ive-level precision with intentional personality.

## When to Use This Skill

Use design-principles when you need to:
- Choose a design direction or personality for an interface
- Select color foundations, typography, or spacing systems
- Make aesthetic decisions about look and feel
- Improve visual hierarchy or polish
- Decide between design approaches (flat vs shadows, dense vs spacious)

**Use frontend-design instead** when you need to write actual HTML/CSS/React code.

## Design Direction (REQUIRED)

**Before writing any code, commit to a design direction.** Don't default. Think about what this specific product needs to feel like.

### Think About Context

- **What does this product do?** A finance tool needs different energy than a creative tool.
- **Who uses it?** Power users want density. Occasional users want guidance.
- **What's the emotional job?** Trust? Efficiency? Delight? Focus?
- **What would make this memorable?** Every product has a chance to feel distinctive.

### Choose a Personality

| Direction | Characteristics | Best For | Examples |
|-----------|-----------------|----------|----------|
| **Precision & Density** | Tight spacing, monochrome, information-forward | Power users who live in the tool | Linear, Raycast |
| **Warmth & Approachability** | Generous spacing, soft shadows, friendly colors | Products that want to feel human | Notion, Coda |
| **Sophistication & Trust** | Cool tones, layered depth, financial gravitas | Money or sensitive data | Stripe, Mercury |
| **Boldness & Clarity** | High contrast, dramatic negative space, confident typography | Modern, decisive feel | Vercel |
| **Utility & Function** | Muted palette, functional density, clear hierarchy | Work matters more than chrome | GitHub |
| **Data & Analysis** | Chart-optimized, technical but accessible | Analytics, metrics, BI | Dashboards |

Pick one. Or blend two. But commit.

### Choose a Color Foundation

| Foundation | Feel | Use When |
|------------|------|----------|
| **Warm** (creams, warm grays) | Approachable, comfortable, human | Collaborative, friendly products |
| **Cool** (slate, blue-gray) | Professional, trustworthy, serious | Enterprise, finance, B2B |
| **Pure neutrals** (true grays, black/white) | Minimal, bold, technical | Developer tools, modern SaaS |
| **Tinted** (slight color cast) | Distinctive, memorable, branded | Products wanting unique identity |

**Light or dark?** Dark feels technical, focused, premium. Light feels open, approachable, clean.

**Accent color** — Pick ONE that means something. Blue for trust. Green for growth. Orange for energy. Violet for creativity.

### Choose Typography

| Type | Feel | Best For |
|------|------|----------|
| **System fonts** | Fast, native, invisible | Utility-focused products |
| **Geometric sans** (Geist, Inter) | Modern, clean, technical | SaaS, developer tools |
| **Humanist sans** (SF Pro, Satoshi) | Warmer, approachable | Consumer, collaborative |
| **Monospace influence** | Technical, data-heavy | Developer tools, analytics |

---

## Core Craft Principles

These apply regardless of design direction. This is the quality floor.

### The 4px Grid

| Spacing | Use |
|---------|-----|
| `4px` | Micro spacing (icon gaps) |
| `8px` | Tight spacing (within components) |
| `12px` | Standard spacing (between related elements) |
| `16px` | Comfortable spacing (section padding) |
| `24px` | Generous spacing (between sections) |
| `32px` | Major separation |

### Symmetrical Padding

**TLBR must match.** If top padding is 16px, left/bottom/right must also be 16px.

```css
/* Good */
padding: 16px;
padding: 12px 16px; /* Only when horizontal needs more room */

/* Bad */
padding: 24px 16px 12px 16px;
```

### Border Radius Consistency

Stick to the 4px grid. Pick a system and commit:
- **Sharp:** 4px, 6px, 8px
- **Soft:** 8px, 12px
- **Minimal:** 2px, 4px, 6px

### Depth & Elevation Strategy

Choose ONE approach and commit:

| Approach | When to Use | CSS |
|----------|-------------|-----|
| **Borders-only** | Utility tools, dense interfaces | `border: 0.5px solid rgba(0,0,0,0.08)` |
| **Subtle single shadow** | Approachable, gentle lift | `0 1px 3px rgba(0,0,0,0.08)` |
| **Layered shadows** | Premium, substantial feel | Multiple layers (see below) |
| **Surface color shifts** | Hierarchy without shadows | Card `#fff` on background `#f8fafc` |

```css
/* Layered shadow approach */
--shadow-layered:
  0 0 0 0.5px rgba(0, 0, 0, 0.05),
  0 1px 2px rgba(0, 0, 0, 0.04),
  0 2px 4px rgba(0, 0, 0, 0.03),
  0 4px 8px rgba(0, 0, 0, 0.02);
```

### Typography Hierarchy

- **Headlines:** 600 weight, tight letter-spacing (-0.02em)
- **Body:** 400-500 weight, standard tracking
- **Labels:** 500 weight, slight positive tracking for uppercase
- **Scale:** 11px, 12px, 13px, 14px (base), 16px, 18px, 24px, 32px

### Monospace for Data

Numbers, IDs, codes, timestamps belong in monospace. Use `tabular-nums` for columnar alignment.

### Iconography

Use **Phosphor Icons** (`@phosphor-icons/react`). Icons clarify, not decorate — if removing an icon loses no meaning, remove it.

### Animation

- 150ms for micro-interactions, 200-250ms for larger transitions
- Easing: `cubic-bezier(0.25, 1, 0.5, 1)`
- No spring/bouncy effects in enterprise UI

### Contrast Hierarchy

Build a four-level system: foreground (primary) → secondary → muted → faint.

### Color for Meaning Only

Gray builds structure. Color only appears when it communicates: status, action, error, success.

---

## Card Design

**Card layouts vary, surface treatment stays consistent.**

Design each card's internal structure for its specific content — but keep consistent: same border weight, shadow depth, corner radius, padding scale, typography.

**Isolated controls:** Date pickers, filters, dropdowns should feel like crafted objects. Never use native `<select>` or `<input type="date">` for styled UI — build custom components.

---

## Dark Mode

- **Borders over shadows** — Shadows less visible on dark. Use borders at 10-15% white opacity.
- **Adjust semantic colors** — Desaturate status colors to avoid harshness.
- **Same structure, different values** — The four-level hierarchy still applies, inverted.

---

## Anti-Patterns

**Never:**
- Dramatic drop shadows (`box-shadow: 0 25px 50px...`)
- Large border radius (16px+) on small elements
- Asymmetric padding without clear reason
- Pure white cards on colored backgrounds
- Thick borders (2px+) for decoration
- Excessive spacing (margins > 48px between sections)
- Spring/bouncy animations
- Gradients for decoration
- Multiple accent colors in one interface

**Always ask:**
- "Did I think about what this product needs, or did I default?"
- "Does this direction fit the context and users?"
- "Is my depth strategy consistent and intentional?"
- "Are all elements on the grid?"

---

## The Standard

Every interface should look designed by a team that obsesses over 1-pixel differences. Not stripped — *crafted*.

The goal: intricate minimalism with appropriate personality. Same quality bar, context-driven execution.

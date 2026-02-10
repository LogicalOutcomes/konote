# Design Foundation — Review Findings & Plan

## Visual Direction Statement

> KoNote's visual identity is calm, clear, and professional. It uses a teal-anchored colour palette with warm neutrals to create an interface that feels trustworthy during long working sessions. The design prioritises readability, accessibility, and emotional restraint — this is software for human services work, and the interface reflects that gravity.

## Consensus Decisions (all 3 reviews agree)

| Decision | Detail |
|----------|--------|
| Primary colour | Teal/blue-green (~`#0d7377` to `#1a7a6d`) |
| Typography | Keep system fonts (Pico defaults), no custom fonts |
| Approach | Separate `theme.css` file for brand identity (swappable per agency), `main.css` for app structure only |
| Background | Warm off-white (`#f8f7f5` to `#fafaf8`), not pure white |
| Dark mode | Plan via CSS variables now, not later |
| Badges | Replace hardcoded hex with semantic token classes |
| Login | Needs wordmark, brand colour, warmth |
| Competitor colours | Penelope = green, Apricot = orange — teal is unclaimed |

## Architecture: Per-Agency Theming

Each agency runs their own KoNote instance and will want their own brand identity. The design system supports this through a clean separation:

| File | Purpose | Agency customisable? |
|------|---------|---------------------|
| `static/css/main.css` | App structure — layouts, badges, timeline, components | No (same everywhere) |
| `static/css/theme.css` | Brand identity — colours, Pico overrides, dark mode | Yes (swap per agency) |
| Phase 6 admin (CUST3) | UI for agencies to set primary colour, logo, product name | Generates CSS variable overrides |

**How it works:**
1. `theme.css` defines all `--kn-*` variables as the KoNote default theme (teal)
2. `main.css` references `--kn-*` variables but never hardcodes colours
3. Agencies can either: replace `theme.css` entirely, or use the admin UI (Phase 6) to override specific variables via an inline `<style>` block in `base.html`
4. The admin-generated overrides sit after `theme.css` in the cascade, so they win

**base.html load order:**
```html
<link rel="stylesheet" href="pico.min.css">    <!-- Framework defaults -->
<link rel="stylesheet" href="theme.css">         <!-- Brand identity (swappable) -->
<link rel="stylesheet" href="main.css">          <!-- App structure -->
{% if agency_theme_css %}
<style>{{ agency_theme_css }}</style>             <!-- Admin overrides (Phase 6) -->
{% endif %}
```

## Proposed Colour Tokens (theme.css)

```css
:root {
  --kn-primary: #0d7377;
  --kn-primary-hover: #0a5c5f;
  --kn-primary-focus: rgba(13, 115, 119, 0.25);
  --kn-secondary: #4a5568;

  --kn-success-bg: #d4edda;  --kn-success-fg: #1a5632;
  --kn-info-bg: #d1ecf1;     --kn-info-fg: #0c5460;
  --kn-warning-bg: #fff3cd;  --kn-warning-fg: #856404;
  --kn-danger-bg: #f8d7da;   --kn-danger-fg: #842029;
  --kn-neutral-bg: #e9ecef;  --kn-neutral-fg: #495057;

  --kn-page-bg: #fafaf8;
  --kn-card-bg: #ffffff;
  --kn-border: #d1d5db;
  --kn-text: #1a202c;
  --kn-text-muted: #718096;
  --kn-text-inverse: #ffffff;

  --kn-section-gap: 2rem;
  --kn-radius-badge: 0.25rem;
  --kn-radius-card: 0.5rem;

  --pico-primary: var(--kn-primary);
  --pico-primary-hover: var(--kn-primary-hover);
  --pico-primary-focus: var(--kn-primary-focus);
  --pico-background-color: var(--kn-page-bg);
}

[data-theme="dark"] {
  --kn-success-bg: #1a3a2a;  --kn-success-fg: #a3d9b1;
  --kn-info-bg: #1a3040;     --kn-info-fg: #90cdf4;
  --kn-warning-bg: #3d2e0a;  --kn-warning-fg: #f6e05e;
  --kn-danger-bg: #3b1a1a;   --kn-danger-fg: #feb2b2;
  --kn-neutral-bg: #2d3748;  --kn-neutral-fg: #cbd5e0;
  --kn-page-bg: var(--pico-background-color);
  --kn-card-bg: #1e2533;
  --kn-border: #4a5568;
  --kn-text: #e2e8f0;
  --kn-text-muted: #a0aec0;
}
```

## Key Warnings from Expert Panel

- Do NOT use red prominently (signals crisis in social services context)
- Do NOT use gamification aesthetics (progress bars as achievements)
- Do NOT use "startup" visuals (gradients, cartoon illustrations, bubbly fonts)
- Do NOT add any CSS framework alongside Pico
- Do NOT use thin font weights (300/light) for body text
- Do NOT rely on colour alone for any status indicator (AODA/WCAG 1.4.1)
- Self-host any custom fonts (PIPEDA) — or just keep system fonts

## Tasks (DES1–DES5, A11Y1)

### DES1: Create theme.css with design tokens
Create `static/css/theme.css` with all `--kn-*` variables and Pico overrides (~80 lines). Update `base.html` to load it between Pico and main.css. Move all colour definitions out of main.css — main.css only references `var(--kn-*)` tokens.

### DES2: Replace badge colours
Change `.badge--active` etc. to `.badge-success`, `.badge-info`, `.badge-warning`, `.badge-danger`, `.badge-neutral` using the `--kn-*` tokens.

### DES3: Redesign login page
- Add "KoNote" wordmark (text-based, styled with CSS — no image needed yet)
- Brand teal accent (border or background element)
- Warm background colour
- Extend base.html instead of standalone page (get the `{% load static %}` tag for free)

### DES4: Empty state and loading patterns
- Empty state: centred text + helpful message + call-to-action button
- Loading: CSS-only progress bar triggered by HTMX `htmx:beforeRequest` / `htmx:afterRequest`
- Success toast: reuse the existing toast pattern from error handler

### DES5: Move login inline styles to CSS
Replace `style="max-width: 420px; margin-top: 10vh;"` with a `.login-container` class.

### A11Y1: Skip nav + aria-live
- Add `<a href="#main-content" class="visually-hidden-focusable">Skip to main content</a>` as first element in body
- Add `id="main-content"` to `<main>`
- Add `aria-live="polite"` to all HTMX target containers (`#client-list`, etc.)
- Add branded focus-visible style (teal outline with offset)

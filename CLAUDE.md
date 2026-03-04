# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Theme Identity

Dawn 15.4.1 by Shopify — an OS 2.0 theme. No build pipeline, no package manager, no transpilation. Files are deployed directly via Shopify CLI.

## Development Commands

```bash
# Deploy theme to a development store (requires Shopify CLI)
shopify theme dev --store=<store-handle>

# Push all files
shopify theme push

# Push a specific file
shopify theme push --only sections/my-section.liquid

# Validate Liquid syntax and schema
shopify theme check

# Validate a single file
shopify theme check sections/my-section.liquid
```

## Architecture

### File roles

| Directory | Role |
|---|---|
| `layout/` | Wraps every page. `theme.liquid` is the root frame. |
| `templates/` | JSON files (preferred) declaring which sections appear on each page type. |
| `sections/` | Configurable page components with `{% schema %}`. Each section is self-contained. |
| `snippets/` | Stateless reusable fragments called via `{% render 'snippet-name' %}`. No schema. |
| `assets/` | Static CSS, JS, images. Referenced via `asset_url` filter. |
| `locales/` | Translation JSON. `en.default.json` is the source of truth. All storefront strings must live here. |
| `config/` | `settings_schema.json` defines global theme settings. `settings_data.json` stores live values. |

### CSS conventions

CSS files are per-component, named `component-[name].css` or `section-[name].css`. Global base styles are in `base.css`. CSS variables for colors and spacing are defined in `snippets/css-variables.liquid` and overridden per section via inline `style` attributes.

- Specificity target: `0 1 0` (single class). Never `!important`, never IDs.
- BEM naming: `block__element--modifier`.
- Mobile-first (`min-width` breakpoints). Max 1 level of nesting except media queries.
- Scope all new CSS to `.section-{{ section.id }}` to avoid bleed.

### JavaScript conventions

All JS is vanilla (no jQuery, no lodash, no frameworks). Scripts use Web Components (`class Foo extends HTMLElement`).

- Private methods use `#privateMethod()` syntax.
- Guard custom element registration: `if (!customElements.get('my-component'))`.
- DOM queries scoped to the section root, not `document`.
- No global event listeners; use event delegation on the component root.
- One script block or JS file per section/component.

## Liquid Rules

- **Never invent filters.** Use only documented Shopify Liquid filters.
- **Multiline logic:** Use `{% liquid %}` blocks.
- **Comments:** `{% # comment %}`.
- **IDs:** CamelCase with section suffix — `id="MyComponent-{{ section.id }}"`.
- **Images:** Always use `image_url` filter with explicit `width:` — never raw CDN URLs.
- **Hierarchy:** JSON templates → sections → snippets (never `include`, always `render`).

## Schema Design Rules

Every section must have a `{% schema %}` with:
- `name`, `tag`, `class`
- All visible text exposed as `settings` or `block.settings`
- Sensible defaults — merchants should never see blank sections out of the box
- Settings ordered top-to-bottom matching visual layout
- Resource pickers (collection/product) before styling settings
- Labels written for non-technical merchants (e.g. "Columns", not "Number of columns"; "Language selector", not "Enable language selector")
- Conditional `"visible_if"` limited to 2 levels deep

**Golden rule:** If marketing might change it → setting or block, never hardcode.

## UI Conversion Rules (HTML → Liquid)

When converting external HTML into Liquid sections:

1. **Rebuild, do not clone.** Reconstruct the UI system from scratch using semantic HTML. Never paste raw HTML into Liquid.
2. **Source of truth:** Rendered UI + computed styles, not class names or inline styles.
3. **Content mapping:** Static text → `section.settings`, repeated items → `blocks`, product data → `product` object, long copy → metafields.
4. **CSS:** Extract visual intent only. Recreate styles separately. Never copy inline styles.
5. **JS:** Ignore competitor JS. Observe the behavior, reimplement cleanly in vanilla JS.
6. **App sections:** Replace with placeholder sections using proper schema so merchants can install apps via Theme Editor.

**Auto-fail conditions:** pasting HTML, preserving competitor class names, hardcoding text/images, using iframes, disabling global CSS.

**Conversion order:** Visual intent → section architecture → schema design → Liquid markup → CSS fidelity → JS behavior. Skipping any step produces broken output.

## Performance Rules

- SSR-first: render all initial content via Liquid. JS is for dynamic behavior only.
- Use `image_url` with `widthStep` for responsive images via Shopify CDN.
- Avoid client-side fetches for content that can be server-rendered.

## Localization

Every string visible to storefront users must be in `locales/en.default.json`. Schema labels use `t:` keys from `locales/en.default.schema.json`. Never hardcode storefront text in Liquid.

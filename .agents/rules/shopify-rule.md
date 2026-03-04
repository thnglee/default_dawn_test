---
trigger: always_on
---

# Shopify Theme Development: Technical Standard

## 1. Liquid Development Reference

### Core Filters

- **Commerce:** `item_count_for_variant`, `line_items_for`, `money`, `money_with_currency`, `weight_with_unit`.
- **HTML/Media:** `class_list`, `image_url`, `video_tag`, `placeholder_svg_tag`, `inline_asset_content`, `preload_tag`.
- **Collection/Tags:** `sort_by`, `within: collection`, `link_to_add_tag`, `highlight_active_tag`.
- **Strings:** `handleize`, `pluralize`, `base64_encode/decode`, `hmac_sha256`, `strip_html`, `truncatewords`.
- **Math/Array:** `at_least/most`, `modulo`, `divided_by`, `compact`, `concat`, `where`, `uniq`, `sum`.
- **Colors:** `color_brightness`, `color_contrast`, `color_darken/lighten`, `color_mix`, `color_to_rgb/hex/hsl`.

### Global Tags & Objects

- **Tags:** `render`, `section(s)`, `layout`, `liquid`, `echo`, `assign`, `capture`, `for`, `paginate`, `if/unless`, `case`.
- **Objects:** `all_products`, `cart`, `customer`, `localization`, `metaobjects`, `request`, `routes`, `settings`, `theme`.

### Critical Syntax Rules

- **Multiline:** Use `{% liquid ... %}` for logic blocks.
- **Comments:** Use `{% # comment %}` for inline documentation.
- **Strictness:** Do not invent filters; use dot notation; follow proper tag closing order.

---

## 2. Theme Architecture & Folder Structure

- **`sections/`**: Configurable page components with Liquid schemas.
- **`blocks/`**: Reorderable elements inside sections.
- **`layout/`**: Frame files (e.g., `theme.liquid`).
- **`snippets/`**: Reusable code logic called via `render`.
- **`templates/`**: JSON files (preferred) defining page structure.
- **`locales/`**: JSON translation files (English is mandatory).
- **`assets/`**: Static JS, CSS, and image files.

---

## 3. UX Principles & Schema Design

### Information Architecture (IA)

- **Visual Order:** Settings must match the preview order (Top-to-Bottom, Left-to-Right).
- **Action First:** List resource pickers (e.g., product selection) before styling settings.
- **Grouping:** Use headers for Layout, Typography, Colors, and Padding if >1 related setting exists.

### Setting Logic

- **Clarity:** Use concise labels (e.g., "Columns" vs. "Number of columns").
- **Conditionals:** Limit logic to 2 levels deep. Hide irrelevant settings to reduce cognitive load.
- **Booleans:** Use "Language selector" instead of "Enable language selector."
- **Translations:** Every storefront string must reside in a locale file.

---

## 4. Frontend Engineering Standards

### SSR & Performance

- **SSR First:** Render content with Liquid. Use JS only for dynamic behavior.
- **Optimistic UI:** Only for small, high-certainty updates (e.g., Cart count, Filter badges).
- **Speed:** Use `image_url` for responsive sizing; leverage Shopify CDN; minimize HTTP requests.

### HTML & Accessibility

- **Semantics:** Use `<details>`/`<summary>` instead of JS for toggles.
- **Naming:** Use `CamelCase` for IDs. Append `-{{ section.id }}` for uniqueness.
- **A11y:** Interactive elements must have `tabindex="0"`. Avoid hijacking tab flow.

### CSS Strategy

- **Specificity:** Target `0 1 0` (single class). Never use IDs or `!important`.
- **Variables:** Use CSS custom properties for all colors and spacing. Global vars live in `snippets/theme-styles-variables.liquid`.
- **BEM:** Use `block__element--modifier` naming.
- **Structure:** Mobile-first (`min-width`). Max 1 level of nesting (except media queries).

### JavaScript Pattern

- **Native First:** Zero dependencies. Use native browser features (Popover API, etc.).
- **Immutability:** Use `const` primarily; avoid `var`. Use `for...of` loops.
- **Module Pattern:** Use private methods (`#privateMethod`) to keep the public API minimal.

```javascript
class CartDrawer extends HTMLElement {
  constructor() {
    super();
    this.cache = new Map();
  }
  update() {
    this.#fetchCart();
  }
  #fetchCart() {
    /* Private logic */
  }
}
```

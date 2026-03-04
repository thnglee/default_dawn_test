---
trigger: always_on
---

# Shopify Theme Development: Strategic Guidelines

## 1. Liquid Reference

### Core Filters

- **Cart/Customer:** `item_count_for_variant`, `line_items_for`, `customer_login_link`, `avatar`, `login_button`.
- **HTML/Media:** `class_list`, `time_tag`, `inline_asset_content`, `highlight`, `link_to`, `placeholder_svg_tag`, `image_tag`, `video_tag`, `image_url`.
- **Collection/Tag:** `sort_by`, `url_for_type`, `within`, `link_to_add_tag`, `link_to_remove_tag`.
- **Color Logic:** `color_brightness`, `color_contrast`, `color_darken/lighten`, `color_mix`, `color_modify`, `color_to_rgb/hex/hsl`.
- **String Ops:** `hmac_sha256`, `base64_encode/decode`, `handleize`, `pluralize`, `strip_html`, `truncatewords`.
- **Math/Array:** `at_least/most`, `modulo`, `plus/minus`, `compact`, `concat`, `find`, `where`, `uniq`, `sum`.
- **Global Assets:** `asset_url`, `file_url`, `shopify_asset_url`, `metafield_tag`.

### Essential Tags & Objects

- **Logic:** `render`, `section(s)`, `layout`, `liquid`, `echo`, `assign`, `capture`, `paginate`.
- **Global Objects:** `all_products`, `cart`, `customer`, `localization`, `metaobjects`, `request`, `routes`, `settings`, `theme`.

### Syntax & Structural Rules

- **Multi-line:** Use `{% liquid ... %}`.
- **Comments:** Use `{% # comment %}`.
- **Strictness:** Never invent filters; use dot notation; respect object scope.
- **Hierarchy:** JSON templates are preferred over Liquid templates for OS 2.0 sections.

---

## 2. Theme Architecture

- **`sections/`**: Configurable components with schemas.
- **`blocks/`**: Reorderable elements within sections.
- **`snippets/`**: Global reusable logic via `render`.
- **`templates/`**: JSON structures defining page sections.
- **`locales/`**: Strict translation keys (English primary).
- **`assets/`**: Static JS/CSS/Images.

---

## 3. UX & Schema Design

### Information Architecture

- **Ordering:** Settings must match visual order (Top → Bottom).
- **Pickers:** Resource pickers (Collection/Product) must appear before styling options.
- **Grouping:** Group related settings under headers (Layout, Typography, Colors, Padding).

### Setting Principles

- **Clarity:** Use "Columns" instead of "Number of columns."
- **Labels:** Use "Language selector" (on/off) instead of "Enable language selector."
- **Conditionals:** Limit to 2 levels deep; avoid "Quick buy" depending on "Swatches."
- **Translations:** Every storefront string must be in locale files.

---

## 4. Engineering Standards

### Performance & SSR

- **SSR First:** Render everything via Liquid; avoid client-side JS for initial content.
- **Optimistic UI:** Allowed only for small, certain updates (e.g., Cart item count, filter checkboxes).
- **Optimization:** Use `image_url` for responsive sizes, minify assets, and use browser caching.

### HTML & Accessibility

- **Semantics:** Use native tags like `<details>`/`<summary>` instead of JS toggles.
- **IDs:** Use `CamelCase` with ID suffixes: `id="MyComponent-{{ section.id }}"`.
- **A11y:** Interactive labels must have `tabindex="0"`. Use `tabindex` only when necessary.

### CSS Strategy

- **Specificity:** Target `0 1 0` (single class). Never use IDs or `!important`.
- **Nesting:** Mobile-first (`min-width`). Max 1 level of nesting (except media queries).
- **BEM:** `block__element--modifier`.
- **Variables:** Use CSS variables for all colors. Reset variables inline: `style="--padding: {{ section.settings.p }}px"`.

### JavaScript Patterns

- **Dependency-Free:** Lean on native browser features (e.g., Popover API).
- **Immutable:** Prefer `const` over `let`; avoid `var`.
- **Module Pattern:** Use private methods (`#methodName`) to minimize public API surface.

```javascript
class ShopifyComponent {
  constructor() {
    this.cache = new Map();
  }
  publicAction() {
    this.#internalLogic();
  }
  #internalLogic() {
    /* Private logic */
  }
}
```

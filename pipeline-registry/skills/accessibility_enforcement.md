# Skill: accessibility_enforcement
# Version: 1.0
# Standard: WCAG 2.1 AA
# Scope: Inject into Section Conversion Agent + Dawn Compliance Agent
# LLM involvement: ARIA label text generation only; all other rules are deterministic

---

## PURPOSE

Ensure every generated Liquid section meets WCAG 2.1 AA accessibility standards and Shopify's accessibility requirements. These rules are non-negotiable. A section that fails accessibility is not shippable.

---

## RULE A11Y-01 — Images Must Have Alt Text

Every `<img>` and `image_tag` output MUST have an `alt` attribute. Never omit it.

**For product images:**
```liquid
{{ product.featured_image | image_url: width: 800 | image_tag: alt: product.featured_image.alt | escape }}
```

**For section setting images:**
```liquid
{{
  section.settings.image
  | image_url: width: 1200
  | image_tag: alt: section.settings.image.alt | escape
}}
```

**For decorative images (intentionally no description):**
```liquid
{{ image | image_url: width: 800 | image_tag: alt: '' }}
```

Never: `image_tag` without an `alt:` parameter.
Never: `alt: image.src` (filename is not alt text).

---

## RULE A11Y-02 — Icon-Only Buttons Must Have Labels

Any button or link with no visible text label MUST have an `aria-label` attribute.

```liquid
<button
  class="button button--icon"
  aria-label="{{ 'sections.cart.close_cart' | t }}"
>
  {% render 'icon-close' %}
</button>
```

For dynamic labels:
```liquid
<button
  class="button button--icon"
  aria-label="{{ 'products.product.media.open_media' | t: index: forloop.index }}"
>
  {% render 'icon-zoom' %}
</button>
```

Never: icon button with no text and no aria-label.

---

## RULE A11Y-03 — Form Inputs Must Be Labelled

Every `<input>`, `<select>`, and `<textarea>` MUST have an associated `<label>` via matching `for`/`id` pair, OR an `aria-label`.

**Preferred (explicit label):**
```liquid
<label for="Email-{{ section.id }}" class="field__label">
  {{ 'newsletter.label' | t }}
</label>
<input
  type="email"
  id="Email-{{ section.id }}"
  name="contact[email]"
  class="field__input"
  autocorrect="off"
  autocapitalize="off"
  autocomplete="email"
  aria-required="true"
>
```

**Acceptable (aria-label when label is not visible):**
```liquid
<input
  type="search"
  id="Search-{{ section.id }}"
  name="q"
  aria-label="{{ 'general.search.search' | t }}"
  class="search__input field__input"
>
```

Never: `<input>` with no `for`/`id` pair and no `aria-label`.

---

## RULE A11Y-04 — Interactive Elements Are Keyboard Accessible

- All interactive elements must be natively focusable (`<a>`, `<button>`, `<input>`, `<select>`, `<textarea>`, `<details>`) OR have `tabindex="0"`.
- Never use `<div>` or `<span>` as click targets without `tabindex="0"` and `role` + keyboard event handler.
- Never use `tabindex` values greater than 0 (breaks tab order).

**Wrong:**
```html
<div class="color-swatch" onclick="selectColor()">Red</div>
```

**Correct:**
```liquid
<button
  class="color-swatch"
  type="button"
  aria-label="{{ 'products.product.color_swatch' | t: color: value }}"
  aria-pressed="{{ pressed }}"
>
  {{ value }}
</button>
```

---

## RULE A11Y-05 — Error Messages Use Live Regions

Form validation errors and async status updates MUST use ARIA live regions so screen readers announce them.

```liquid
<div
  id="CartErrors-{{ section.id }}"
  role="alert"
  aria-live="polite"
  aria-atomic="true"
>
  <!-- Error messages injected here by JS -->
</div>
```

For loading states:
```liquid
<div
  id="LoadingStatus-{{ section.id }}"
  role="status"
  aria-live="polite"
  aria-hidden="true"
>
  {{ 'accessibility.loading' | t }}
</div>
```

---

## RULE A11Y-06 — Carousels and Sliders

Any carousel or slider MUST include:
- `role="region"` on the outer container with `aria-label`
- `aria-roledescription="carousel"` on the track
- `aria-label` on each slide
- Previous/next buttons with descriptive `aria-label`
- Live region announcing current slide

```liquid
<section
  class="slideshow"
  aria-label="{{ section.settings.accessibility_info | default: section.settings.heading | escape }}"
  aria-roledescription="carousel"
>
  <div class="slideshow__slides" aria-live="polite" aria-atomic="true">
    {%- for block in section.blocks -%}
      <div
        class="slideshow__slide"
        role="group"
        aria-roledescription="slide"
        aria-label="{{ forloop.index }} {{ 'accessibility.of' | t }} {{ forloop.length }}"
        {{ block.shopify_attributes }}
      >
        <!-- slide content -->
      </div>
    {%- endfor -%}
  </div>

  <button class="slideshow__btn slideshow__btn--prev" aria-label="{{ 'sections.slideshow.previous_slideshow' | t }}">
    {% render 'icon-caret' %}
  </button>
  <button class="slideshow__btn slideshow__btn--next" aria-label="{{ 'sections.slideshow.next_slideshow' | t }}">
    {% render 'icon-caret' %}
  </button>
</section>
```

---

## RULE A11Y-07 — Modals and Drawers

Every modal, drawer, and dialog MUST include:
- `role="dialog"` or `<dialog>` element
- `aria-modal="true"`
- `aria-labelledby` pointing to the dialog title
- Focus trap (managed in JS)
- Close button with descriptive `aria-label`

```liquid
<dialog
  id="CartDrawer"
  class="cart-drawer"
  aria-modal="true"
  aria-labelledby="CartDrawer-Title"
>
  <div class="cart-drawer__header">
    <h2 id="CartDrawer-Title" class="cart-drawer__heading">
      {{ 'sections.cart.title' | t }}
    </h2>
    <button
      class="button button--icon cart-drawer__close"
      aria-label="{{ 'accessibility.close' | t }}"
    >
      {% render 'icon-close' %}
    </button>
  </div>
  <!-- drawer content -->
</dialog>
```

---

## RULE A11Y-08 — Color Contrast

- Do not hardcode any color pair where contrast ratio cannot be verified.
- All text must meet WCAG AA: 4.5:1 for normal text, 3:1 for large text (18px+ or 14px+ bold).
- When using Dawn color schemes, contrast is managed by the theme. Do not override scheme colors without verifying contrast.
- Flag any `color` or `background-color` values not derived from Dawn CSS variables.

Emit a warning comment when contrast cannot be confirmed:
```liquid
{%- comment -%}
  A11Y WARNING: Hardcoded color used here. Verify contrast ratio ≥ 4.5:1 against background.
{%- endcomment -%}
```

---

## RULE A11Y-09 — Reduced Motion

All CSS animations and transitions must respect user preference:

```css
@media (prefers-reduced-motion: no-preference) {
  .my-section__element {
    transition: opacity 0.3s ease;
    animation: fadeIn 0.4s ease forwards;
  }
}
```

Never animate outside this media query. Dawn's `animations.js` uses IntersectionObserver with reduced-motion detection — use Dawn's `data-cascade` pattern instead of custom animation.

---

## RULE A11Y-10 — Semantic HTML

Use native semantic elements. Do not reimplement native behavior with divs and JS.

| Instead of | Use |
|---|---|
| `<div class="accordion">` + JS | `<details>`/`<summary>` |
| `<div class="tab">` + JS | `<details>` or ARIA tabs pattern |
| `<div class="button">` + JS | `<button type="button">` |
| `<div class="list">` | `<ul>` or `<ol>` |
| `<div class="nav">` | `<nav aria-label="...">` |
| `<div class="header">` | `<header>` |
| `<div class="footer">` | `<footer>` |
| `<b>` for emphasis | `<strong>` |
| `<i>` for emphasis | `<em>` |

---

## RULE A11Y-11 — Skip Links

If the section contains navigation (header, mega-menu) a skip link must exist pointing to the main content:

```liquid
<a href="#MainContent" class="skip-to-content-link button visually-hidden">
  {{ 'accessibility.skip_to_text' | t }}
</a>
```

Dawn's `layout/theme.liquid` provides this globally. Only add it in custom layout overrides.

---

## RULE A11Y-12 — Tables

Data tables must have `<th>` headers with `scope` attributes:

```liquid
<table>
  <thead>
    <tr>
      <th scope="col">{{ 'sections.size_chart.size' | t }}</th>
      <th scope="col">{{ 'sections.size_chart.chest' | t }}</th>
    </tr>
  </thead>
  <tbody>
    {%- for row in section.blocks -%}
      <tr>
        <td>{{ row.settings.size }}</td>
        <td>{{ row.settings.chest }}</td>
      </tr>
    {%- endfor -%}
  </tbody>
</table>
```

---

## DETERMINISTIC CHECKS (run without LLM)

These can be verified by static analysis tools or regex before involving an LLM:

| Check | Pattern to detect violation |
|---|---|
| Missing alt on image_tag | `image_tag` without `alt:` |
| Icon button without label | `button--icon` class with no `aria-label` |
| Input without label | `<input` not followed by matching `<label for` within 5 lines |
| Animation outside reduced-motion | `animation:` or `transition:` outside `@media (prefers-reduced-motion)` |
| Hardcoded color override | `color: #` or `background-color: #` in section CSS |
| Missing dialog attributes | `role="dialog"` without `aria-modal` |
| tabindex > 0 | `tabindex="[1-9]` |

---

## LLM-ONLY CHECKS (require semantic reasoning)

- ARIA label text quality (is it descriptive and useful, not just "button"?)
- Alt text accuracy (does it describe the actual image content?)
- Heading hierarchy (are h1/h2/h3 levels semantically correct for the page?)
- Error message clarity (is the message actionable for the user?)

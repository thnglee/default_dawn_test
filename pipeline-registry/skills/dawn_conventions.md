# Skill: dawn_conventions
# Version: dawn-15.0
# Pinned to: Dawn theme v15.4.x
# Scope: Inject into Section Conversion Agent + Dawn Compliance Agent
# Update trigger: Any Dawn major or minor release

---

## PURPOSE

Enforce Dawn-specific patterns in every generated Liquid section. This is not generic Shopify — it is Dawn-specific. Generated sections must be indistinguishable from native Dawn sections in structure and behavior.

---

## RULE DC-01 — Schema: Required Keys

Every section's `{% schema %}` MUST include:

```json
{
  "name": "Section Display Name",
  "tag": "section",
  "class": "section-identifier",
  "disabled_on": {
    "groups": ["header", "footer"]
  },
  "settings": [],
  "blocks": [],
  "presets": [
    { "name": "Section Display Name" }
  ]
}
```

Missing `tag`, `class`, or `presets` = schema error.

---

## RULE DC-02 — CSS Scoping

All section CSS must be scoped. Two accepted patterns:

**Pattern A — Inline `{% style %}` block (preferred for sections):**
```liquid
{% style %}
  .section-{{ section.id }} {
    padding-top: {{ section.settings.padding_top }}px;
    padding-bottom: {{ section.settings.padding_bottom }}px;
  }
{% endstyle %}
```

**Pattern B — External asset file:**
```liquid
{{ 'section-my-section.css' | asset_url | stylesheet_tag }}
```

Never write unscoped CSS that could affect other sections.

---

## RULE DC-03 — Padding Schema Pattern

All sections that have spacing MUST expose padding via these exact setting IDs:

```json
{
  "type": "range",
  "id": "padding_top",
  "min": 0,
  "max": 100,
  "step": 4,
  "unit": "px",
  "label": "t:sections.all.padding_top",
  "default": 36
},
{
  "type": "range",
  "id": "padding_bottom",
  "min": 0,
  "max": 100,
  "step": 4,
  "unit": "px",
  "label": "t:sections.all.padding_bottom",
  "default": 36
}
```

---

## RULE DC-04 — Color Scheme

Use Dawn's color scheme selector pattern for sections that need background color control:

```json
{
  "type": "color_scheme",
  "id": "color_scheme",
  "label": "t:sections.all.color_scheme.label",
  "default": "scheme-1"
}
```

In Liquid:
```liquid
<div class="color-{{ section.settings.color_scheme }} gradient">
```

Never hardcode background colors. Never use a `type: "color"` setting for section background.

---

## RULE DC-05 — Image Settings

```json
{
  "type": "image_picker",
  "id": "image",
  "label": "Image"
}
```

Rendering pattern:
```liquid
{%- if section.settings.image != blank -%}
  {{
    section.settings.image
    | image_url: width: 1500
    | image_tag:
      widths: '375, 550, 750, 1100, 1500, 1780',
      sizes: '(min-width: 1200px) calc((100vw - 10rem) / 2), (min-width: 750px) calc((100vw - 11.5rem) / 2), calc(100vw - 4rem)',
      class: 'my-section__image',
      loading: 'lazy',
      alt: section.settings.image.alt | escape
  }}
{%- else -%}
  {{ 'image' | placeholder_svg_tag: 'placeholder-svg' }}
{%- endif -%}
```

---

## RULE DC-06 — Typography: Heading Sizes

Use Dawn's heading size selector, not custom font-size values:

```json
{
  "type": "select",
  "id": "heading_size",
  "options": [
    { "value": "h2", "label": "t:sections.all.heading_size.options__1.label" },
    { "value": "h3", "label": "t:sections.all.heading_size.options__2.label" },
    { "value": "h4", "label": "t:sections.all.heading_size.options__4.label" }
  ],
  "default": "h2",
  "label": "t:sections.all.heading_size.label"
}
```

In Liquid:
```liquid
<{{ section.settings.heading_size }} class="my-section__heading">
  {{ section.settings.heading | escape }}
</{{ section.settings.heading_size }}>
```

---

## RULE DC-07 — Buttons

Use Dawn's button classes exclusively. Never write custom button styles.

| Intent | Class |
|---|---|
| Primary CTA | `button button--primary` |
| Secondary/outline | `button button--secondary` |
| Full width | `button button--full-width` |
| Icon only | `button button--icon` |

```liquid
<a href="{{ section.settings.button_url }}" class="button button--primary">
  {{ section.settings.button_label | escape }}
</a>
```

---

## RULE DC-08 — Page Width Container

Every section's inner content container must use Dawn's page-width class:

```liquid
<div class="page-width">
  <!-- section content -->
</div>
```

For full-bleed sections:
```liquid
<section class="my-section color-{{ section.settings.color_scheme }} gradient">
  <div class="my-section__inner page-width">
    <!-- section content -->
  </div>
</section>
```

---

## RULE DC-09 — Grid Layout

Use Dawn's grid utility classes, not custom flex/grid CSS:

| Columns | Class |
|---|---|
| 2 col (tablet+) | `grid grid--2-col-tablet` |
| 3 col (desktop) | `grid grid--3-col-desktop` |
| 4 col (desktop) | `grid grid--4-col-desktop` |
| 2 col (mobile) | `grid grid--2-col-tablet-down` |

```liquid
<ul class="grid grid--2-col-tablet grid--4-col-desktop">
  {%- for block in section.blocks -%}
    <li class="grid__item">...</li>
  {%- endfor -%}
</ul>
```

---

## RULE DC-10 — Animations

Use Dawn's `data-cascade` attribute for staggered entrance animations. Do not write custom IntersectionObserver code.

```liquid
<ul class="grid" role="list">
  {%- for block in section.blocks -%}
    <li class="grid__item" {{ block.shopify_attributes }}>
      <div data-cascade style="--animation-order: {{ forloop.index }};">
        <!-- block content -->
      </div>
    </li>
  {%- endfor -%}
</ul>
```

---

## RULE DC-11 — JavaScript: Web Component Pattern

All custom JavaScript MUST use the Web Component pattern. No inline `<script>` in section HTML that accesses the DOM directly.

```liquid
<script>
  if (!customElements.get('my-component')) {
    customElements.define('my-component', class MyComponent extends HTMLElement {
      constructor() {
        super();
      }

      connectedCallback() {
        this.#init();
      }

      #init() {
        // private initialization
      }
    });
  }
</script>
```

Rules:
- Guard with `if (!customElements.get('...'))` always
- DOM queries scoped to `this` or `this.querySelector`
- No `document.querySelector` inside component methods
- No `var`, no jQuery, no external libraries
- Private methods use `#` prefix

---

## RULE DC-12 — Font Inheritance

Never set `font-family` in section CSS. Inherit from theme settings.

```css
/* WRONG */
.my-section__heading {
  font-family: 'Helvetica', sans-serif;
}

/* CORRECT — Dawn variables are set by snippets/css-variables.liquid */
.my-section__heading {
  font-family: var(--font-heading-family);
  font-weight: var(--font-heading-weight);
}
```

---

## RULE DC-13 — Focus States

Use Dawn's utility class. Never write custom `outline` styles.

```liquid
<button class="button button--primary focus-inset">
```

For link focus:
```css
.my-section__link:focus-visible {
  outline: 0.3rem solid rgba(var(--color-foreground), 0.5);
  outline-offset: 0.3rem;
}
```

---

## RULE DC-14 — Shopify Attributes on Blocks

Every block's root element MUST include `{{ block.shopify_attributes }}` to enable Theme Editor highlighting.

```liquid
{%- for block in section.blocks -%}
  <div class="my-block" {{ block.shopify_attributes }}>
    ...
  </div>
{%- endfor -%}
```

---

## RULE DC-15 — Locale Keys in Schema

Schema `label` and `info` fields MUST use `t:` translation keys, not hardcoded English strings — unless it is a new section with no existing locale key, in which case a new key MUST be added to `locales/en.default.schema.json`.

```json
"label": "t:sections.all.heading_size.label"      ← correct
"label": "Heading size"                             ← fail (not translatable)
```

---

## RULE DC-16 — Disabled On

Sections that are not appropriate in the header or footer must declare:

```json
"disabled_on": {
  "groups": ["header", "footer"]
}
```

Sections designed specifically for the header or footer must declare the opposite:
```json
"enabled_on": {
  "groups": ["header"]
}
```

---

## DAWN NATIVE SNIPPETS AVAILABLE

Do not reimplement these — always render:

| Snippet | Use |
|---|---|
| `card-product` | Product card in any grid |
| `card-article` | Blog article card |
| `price` | Price display with sale state |
| `quantity-input` | Quantity stepper |
| `pagination` | Page pagination |
| `facets` | Collection filters |
| `header-search` | Search form |
| `social-icons` | Social media links |
| `icon-[name]` | SVG icon inline |
| `css-variables` | Injected via layout, not needed in sections |
| `theme-editor-support` | Injected via layout |

---

## COMPLIANCE SCORING

A section scores below threshold (0.7) if it violates any of:
- DC-01 (missing schema keys)
- DC-02 (unscoped CSS)
- DC-04 (hardcoded background color)
- DC-07 (custom button styles)
- DC-11 (inline DOM scripts)
- DC-14 (missing shopify_attributes)
- DC-15 (hardcoded schema labels)

These are not warnings — they are errors.

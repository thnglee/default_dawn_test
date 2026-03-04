# Skill: html_to_liquid
# Version: 1.2
# Scope: Inject into Section Conversion Agent system prompt
# Trigger: Every section conversion call

---

## PURPOSE

Convert competitor HTML snippets into Shopify-native Liquid. This is UI reconstruction, not markup translation. The HTML is a reference — never copy it directly.

---

## RULE HL-01 — Never Paste HTML

NEVER output raw HTML copied from the source.
Rebuild the DOM from semantic intent.
If you cannot determine the semantic intent → ask for clarification. Do not guess.

---

## RULE HL-02 — Content Mapping

Map every visible content element to the correct Liquid binding:

| Source Content | Liquid Target |
|---|---|
| Static headline text | `section.settings.[id]` (type: text) |
| Static body/paragraph | `section.settings.[id]` (type: richtext) |
| Repeated card/item | `section.blocks` (one block per item) |
| Product title | `{{ product.title }}` |
| Product price | `{{ product.price | money }}` |
| Product compare-at price | `{{ product.compare_at_price | money }}` |
| Product description | `{{ product.description }}` |
| Product vendor | `{{ product.vendor }}` |
| Product images | `{% for image in product.images %}` |
| Variant options | `{% for option in product.options_with_values %}` |
| Product URL | `{{ product.url }}` |
| Collection title | `{{ collection.title }}` |
| Article content | `{{ article.content }}` |
| Long marketing copy | `{{ product.metafields.custom.[key] }}` |

Forbidden bindings:
- Hardcoded product names, prices, or SKUs
- External image URLs (CDN not hosted on Shopify)
- Base64-encoded images
- Hardcoded collection or product handles

---

## RULE HL-03 — Image Rendering

ALWAYS use the `image_url` filter with an explicit width. Never use raw `src` attributes pointing to competitor CDNs.

```liquid
{{ image | image_url: width: 800 | image_tag: loading: 'lazy', alt: image.alt }}
```

For responsive images with srcset:
```liquid
{{
  image
  | image_url: width: 1500
  | image_tag:
    widths: '375, 550, 750, 1100, 1500',
    sizes: '(min-width: 1200px) 50vw, 100vw',
    loading: 'lazy',
    alt: image.alt
}}
```

For background images via CSS variable:
```liquid
style="--bg-image: url('{{ image | image_url: width: 1500 }}')"
```

---

## RULE HL-04 — Repeated Patterns → Blocks

Any content that repeats (swatches, feature bullets, cards, tabs, FAQs, testimonials) MUST become a `block` type in the schema — never a hardcoded loop.

```liquid
{%- for block in section.blocks -%}
  {%- case block.type -%}
    {%- when 'feature_item' -%}
      <li class="feature-list__item" {{ block.shopify_attributes }}>
        {{ block.settings.text }}
      </li>
  {%- endcase -%}
{%- endfor -%}
```

---

## RULE HL-05 — Links

| Source | Liquid Output |
|---|---|
| `/products/[handle]` | `{{ product.url }}` |
| `/collections/[handle]` | `{{ collection.url }}` |
| `/pages/[handle]` | Use `section.settings.button_url` (type: url) |
| `/` | `{{ routes.root_url }}` |
| `/cart` | `{{ routes.cart_url }}` |
| `/account` | `{{ routes.account_url }}` |

Never hardcode path strings.

---

## RULE HL-06 — Add-to-Cart Buttons

Use Dawn's `product-form` web component and the `product-form.liquid` snippet pattern.

```liquid
{%- form 'product', product, id: 'product-form-{{ section.id }}', novalidate: 'novalidate' -%}
  <input type="hidden" name="id" value="{{ product.selected_or_first_available_variant.id }}">
  <button
    type="submit"
    name="add"
    class="button button--full-width button--primary"
    {% if product.selected_or_first_available_variant.available == false %}disabled{% endif %}
  >
    {%- if product.selected_or_first_available_variant.available -%}
      {{ 'products.product.add_to_cart' | t }}
    {%- else -%}
      {{ 'products.product.sold_out' | t }}
    {%- endif -%}
  </button>
{%- endform -%}
```

---

## RULE HL-07 — Variant Selectors

Variant options must use `product.options_with_values` — never hardcoded option lists.

```liquid
{%- for option in product.options_with_values -%}
  <fieldset class="product-form__input product-form__input--pill">
    <legend class="form__label">{{ option.name }}</legend>
    {%- for value in option.values -%}
      <input
        type="radio"
        id="{{ section.id }}-{{ option.position }}-{{ forloop.index0 }}"
        name="{{ option.name }}"
        value="{{ value | escape }}"
        {% if option.selected_value == value %}checked{% endif %}
      >
      <label for="{{ section.id }}-{{ option.position }}-{{ forloop.index0 }}">
        {{ value }}
      </label>
    {%- endfor -%}
  </fieldset>
{%- endfor -%}
```

---

## RULE HL-08 — Icons

- Inline SVG only if ≤ 10 lines
- For Dawn-native icons: `{% render 'icon-arrow' %}`, `{% render 'icon-cart' %}` etc.
- Never link to external icon fonts (Font Awesome, Material Icons)
- Icon-only interactive elements MUST have `aria-label`

---

## RULE HL-09 — Quantity Input

Use Dawn's existing snippet:
```liquid
{% render 'quantity-input' %}
```

Never reimplement quantity input from scratch.

---

## RULE HL-10 — Tabs / Accordions

Use `<details>`/`<summary>` for accordions. No JS toggle required.

```liquid
<details class="accordion" id="Accordion-{{ section.id }}-{{ forloop.index }}">
  <summary class="accordion__title">
    {{ block.settings.heading }}
    {% render 'icon-caret' %}
  </summary>
  <div class="accordion__content rte">
    {{ block.settings.content }}
  </div>
</details>
```

---

## RULE HL-11 — No Hardcoded IDs or Handles

Forbidden:
```liquid
{% assign featured = all_products['my-product-handle'] %}   ← FAIL
```

Correct:
```liquid
{% assign featured = section.settings.product %}            ← PASS
```

---

## RULE HL-12 — Price Display

Always handle sale state:

```liquid
<div class="price {% if product.compare_at_price > product.price %}price--on-sale{% endif %}">
  <span class="price__current">{{ product.price | money }}</span>
  {%- if product.compare_at_price > product.price -%}
    <s class="price__compare">{{ product.compare_at_price | money }}</s>
  {%- endif -%}
</div>
```

---

## RULE HL-13 — Video

```liquid
{%- if section.settings.video != blank -%}
  {{ section.settings.video | video_tag: autoplay: false, loop: section.settings.loop, muted: true }}
{%- elsif section.settings.video_url != blank -%}
  <iframe
    src="{{ section.settings.video_url }}"
    title="{{ section.settings.video_title | escape }}"
    allow="autoplay; encrypted-media"
    allowfullscreen
    loading="lazy"
  ></iframe>
{%- endif -%}
```

---

## SELF-CHECK BEFORE OUTPUT

Before finalizing any section conversion, confirm:

- [ ] No raw HTML pasted
- [ ] No hardcoded text (all in `section.settings` or `block.settings`)
- [ ] No hardcoded product handles or IDs
- [ ] No external image URLs
- [ ] No `$XX.XX` price strings anywhere in output
- [ ] All repeated elements are blocks
- [ ] All links use `routes.*` or settings type `url`
- [ ] Images use `image_url` filter
- [ ] Icons use `render 'icon-*'` or inline SVG ≤ 10 lines
- [ ] Add-to-cart uses product form pattern
- [ ] All locale strings use `t:` keys

If any check fails → fix before outputting. Do not ship with known violations.

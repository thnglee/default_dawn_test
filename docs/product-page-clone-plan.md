# Sculptique Product Page — Shopify Liquid Clone Plan

**Reference:** `trysculptique.com/products/lymph-cc-select`
**Theme Base:** Dawn (OS 2.0)
**Third-party App:** Kaching Bundles (hero offer box — rendered via App Block)
**Goal:** Full Shopify-native, merchant-editable product page that matches the reference screenshot with support for 3rd-party app integration.

---

## Architecture Overview

The product page is composed of **10 distinct visual sections**, each mapped to a Shopify `section/*.liquid` file registered in `templates/product.json`.

```
templates/product.json
│
├── [1] product-hero              ← Main product + Kaching Bundle App Block
├── [2] product-benefits          ← Icon list of key benefits
├── [3] product-education         ← "Why This Happens After 35" editorial
├── [4] product-ingredients       ← Ingredient highlight cards
├── [5] product-stats             ← % stat circles (87%, 91%)
├── [6] product-social-proof      ← Photo testimonials / video wall
├── [7] product-expert-panel      ← Clinician quote + credibility
├── [8] product-faq               ← Collapsible Q&A
├── [9] product-guarantee         ← Subscription / refill offer bar
└── [10] product-related          ← Related products (existing Dawn section)
```

---

## Phase 0 — Environment & Conventions (0.5 hr)

**Goal:** Establish naming conventions, file structure, and shared design tokens before writing any code.

### 0.1 Create the docs folder (done)

File: `docs/product-page-clone-plan.md` (this file)

### 0.2 Design Token File

Create `snippets/product-theme-vars.liquid` — CSS custom property declarations shared across all product sections:

```css
:root {
  --color-brand-green: #3d6b4e;
  --color-brand-cream: #f5f0e8;
  --color-brand-pink: #f2a0a0;
  --color-brand-dark: #1a1a1a;
  --color-accent-light: #e8f4ec;
  --font-heading: "Playfair Display", serif;
  --font-body: "Inter", sans-serif;
  --radius-card: 12px;
  --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.08);
}
```

Render this snippet once inside `layout/theme.liquid` before `</head>`.

### 0.3 Google Fonts

Add to `layout/theme.liquid`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link
  href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap"
  rel="stylesheet"
/>
```

### 0.4 App Block Compatibility Pattern

Every section that may host a 3rd-party app block must include this block type declaration in its schema:

```json
{
  "type": "@app"
}
```

And render it in the section template:

```liquid
{% for block in section.blocks %}
  {% if block.type == '@app' %}
    {% render block %}
  {% endif %}
{% endfor %}
```

---

## Phase 1 — Hero Section: Product Info + Kaching Bundle (2 hr)

**File:** `sections/product-hero.liquid`
**CSS:** `assets/product-hero.css`
**JS:** `assets/product-hero.js`

### 1.1 Layout Structure

```
.product-hero
├── .product-hero__media          ← Left: image gallery + sub-images grid
│   ├── .product-hero__badge      ← "Spring Sale" circle badge (section setting)
│   ├── .product-hero__main-img   ← Primary product image
│   └── .product-hero__thumbnails ← 2×3 sub-image grid (editorial images)
└── .product-hero__info           ← Right: all purchase info
    ├── .product-hero__rating     ← Star rating + "Based on X Reviews"
    ├── .product-hero__title      ← product.title
    ├── .product-hero__trust-icons ← Icon list (24hr cycle, fluid retention, etc.)
    ├── .product-hero__clinician  ← Clinician Choice badge row
    ├── [APP BLOCK AREA]          ← Kaching Bundles renders here
    ├── .product-hero__delivery   ← "Delivered on [date] with Express Shipping"
    ├── .product-hero__cta        ← ADD TO CART button
    └── .product-hero__assurance  ← "Refills / Cancel Anytime" strip
```

### 1.2 Media Gallery

- Use `product.media` for the main image.
- Sub-images: editorial lifestyle images kept as `image_picker` blocks (up to 6).
- "Nutritional Information" overlay button → opens a `<dialog>` overlay with metafield content.
- JS: clicking a thumbnail swaps the main image (native DOM, no framework).

```liquid
{% comment %} Main image {% endcomment %}
{{ product.featured_media | image_url: width: 800 | image_tag: class: 'product-hero__main-img', loading: 'eager' }}
```

### 1.3 Trust Icon List

Each icon+text pair is a block of type `trust_item`:

```json
{
  "type": "trust_item",
  "name": "Trust Item",
  "settings": [
    { "type": "image_picker", "id": "icon", "label": "Icon" },
    { "type": "richtext", "id": "text", "label": "Benefit text" }
  ]
}
```

### 1.4 Rating Bar

Settings:

- `rating_score` — range 4.0–5.0 (default: 4.8)
- `rating_label` — text (default: "Excellent")
- `review_count` — number

Render five filled/half SVG stars via Liquid math:

```liquid
{% assign full_stars = section.settings.rating_score | floor %}
```

### 1.5 Kaching Bundle Integration (App Block)

> **KEY REQUIREMENT:** The **offer/bundle selector box** (1 bottle / Buy 2 Get 1 / Buy 3 Get 2) is rendered by **Kaching Bundles**. The theme must expose an `@app` block slot so merchants install and position the app block via the Theme Editor.

Schema declaration:

```json
{
  "type": "@app"
},
{
  "type": "app_placeholder",
  "name": "Bundle Selector Placeholder",
  "settings": [
    {
      "type": "paragraph",
      "content": "Install the Kaching Bundles app and add its block above this placeholder. This placeholder will be hidden when an app block is present."
    }
  ]
}
```

Render order in template:

1. `trust_item` blocks
2. `clinician_badge` block
3. `@app` blocks (Kaching Bundles renders here)
4. Delivery estimate strip
5. Add to Cart button (fallback if no app block active)
6. Assurance strip

### 1.6 Delivery Estimate Strip

Dynamic date using Liquid + JS fallback:

```liquid
<p class="product-hero__delivery">
  Delivered on
  <strong class="product-hero__delivery-date js-delivery-date">Monday, 9 March</strong>
  with <span>Express Shipping</span>
</p>
```

JS calculates +5 business days and replaces `.js-delivery-date` on DOM ready (no hydration mismatch since it's non-critical).

### 1.7 Add To Cart (Fallback)

Render `snippets/buy-buttons.liquid` inside a conditional:

```liquid
{% unless section.blocks | where: 'type', '@app' | size > 0 %}
  {% render 'buy-buttons', product: product, block: block, product_form_id: product_form_id %}
{% endunless %}
```

### 1.8 Schema Summary

| Setting           | Type     | Purpose                                  |
| ----------------- | -------- | ---------------------------------------- |
| `badge_text`      | text     | "Spring Sale" badge label                |
| `badge_color`     | color    | Badge background                         |
| `rating_score`    | range    | Star rating number                       |
| `rating_label`    | text     | "Excellent" label                        |
| `review_count`    | number   | Review count                             |
| `clinician_count` | number   | "521 clinicians"                         |
| `delivery_label`  | text     | Delivery CTA text                        |
| `assurance_text`  | richtext | "Refills every 8 weeks / Cancel anytime" |

---

## Phase 2 — Benefits Section (0.5 hr)

**File:** `sections/product-benefits.liquid`
**CSS:** `assets/product-benefits.css`

### 2.1 Layout

Full-width cream background (`--color-brand-cream`). Three to four columns of benefit cards:

```
.product-benefits
└── .product-benefits__grid
    └── .product-benefits__item (repeating block)
        ├── .product-benefits__icon   ← SVG or image_picker
        └── .product-benefits__text   ← richtext
```

### 2.2 Block: `benefit_item`

```json
{
  "type": "benefit_item",
  "name": "Benefit",
  "limit": 6,
  "settings": [
    { "type": "image_picker", "id": "icon", "label": "Icon" },
    { "type": "inline_richtext", "id": "headline", "label": "Headline" },
    { "type": "richtext", "id": "description", "label": "Description" }
  ]
}
```

### 2.3 Section Settings

| Setting            | Type       | Default                 |
| ------------------ | ---------- | ----------------------- |
| `heading`          | text       | "Why Our Formula Works" |
| `background_color` | color      | `#f5f0e8`               |
| `columns_desktop`  | range 2–4  | 3                       |
| `columns_mobile`   | select 1–2 | 1                       |

---

## Phase 3 — Education / Editorial Section (1 hr)

**File:** `sections/product-education.liquid`
**CSS:** `assets/product-education.css`

### 3.1 Layout

Two-column layout. Left: headline + body copy. Right: lifestyle image.

```
.product-education
├── .product-education__text
│   ├── h2.product-education__heading
│   ├── p.product-education__subheading (pink accent)
│   └── .product-education__body (richtext)
└── .product-education__media
    └── img (image_picker)
```

### 3.2 Block: `education_point`

For bullet points / icon-text pairs within the body:

```json
{
  "type": "education_point",
  "name": "Key Point",
  "settings": [
    { "type": "image_picker", "id": "icon", "label": "Icon" },
    { "type": "inline_richtext", "id": "text", "label": "Text" }
  ]
}
```

### 3.3 Section Settings

| Setting            | Type                |
| ------------------ | ------------------- |
| `heading`          | text                |
| `subheading`       | text                |
| `body`             | richtext            |
| `image`            | image_picker        |
| `image_position`   | select (left/right) |
| `background_color` | color               |

---

## Phase 4 — Ingredients Section (0.75 hr)

**File:** `sections/product-ingredients.liquid`
**CSS:** `assets/product-ingredients.css`

### 4.1 Layout

Full-width section. Small header. Horizontal scrollable cards (mobile) / grid (desktop).

```
.product-ingredients
├── .product-ingredients__header
│   ├── h2 (section heading)
│   └── p (subheading)
└── .product-ingredients__grid
    └── .product-ingredients__card (block)
        ├── img  ← ingredient image
        ├── h3   ← ingredient name
        └── p    ← short description
```

### 4.2 Block: `ingredient`

```json
{
  "type": "ingredient",
  "name": "Ingredient",
  "limit": 8,
  "settings": [
    { "type": "image_picker", "id": "image", "label": "Image" },
    { "type": "text", "id": "name", "label": "Ingredient Name" },
    { "type": "richtext", "id": "description", "label": "Description" }
  ]
}
```

### 4.3 @app Block Slot

Include `@app` in blocks array to allow ingredient-level app integrations (e.g., third-party supplement verifier badges) in the future.

---

## Phase 5 — Stats / Social Proof Numbers (0.5 hr)

**File:** `sections/product-stats.liquid`
**CSS:** `assets/product-stats.css`

### 5.1 Layout

Two large circular progress indicators side-by-side:

```
.product-stats__grid
├── .product-stats__item
│   ├── .product-stats__circle  ← SVG ring (% driven by CSS custom prop)
│   ├── .product-stats__percent ← "87%"
│   └── .product-stats__label  ← richtext label
└── ...
```

SVG ring pattern:

```html
<svg viewBox="0 0 120 120">
  <circle class="product-stats__track" cx="60" cy="60" r="54" />
  <circle
    class="product-stats__fill"
    cx="60"
    cy="60"
    r="54"
    style="--pct: {{ block.settings.percentage }}"
  />
</svg>
```

CSS:

```css
.product-stats__fill {
  stroke-dasharray: calc(var(--pct) * 3.3929) 339.29;
}
```

### 5.2 Block: `stat_item`

```json
{
  "type": "stat_item",
  "name": "Stat",
  "limit": 4,
  "settings": [
    {
      "type": "range",
      "id": "percentage",
      "min": 0,
      "max": 100,
      "label": "Percentage"
    },
    { "type": "richtext", "id": "label", "label": "Label text" },
    {
      "type": "color",
      "id": "ring_color",
      "label": "Ring color",
      "default": "#3d6b4e"
    }
  ]
}
```

---

## Phase 6 — Social Proof / Testimonials (1 hr)

**File:** `sections/product-testimonials.liquid`
**CSS:** `assets/product-testimonials.css`
**JS:** `assets/product-testimonials.js`

### 6.1 Layout

Section heading. Horizontal testimonial cards with photo + name + quote + star rating.

```
.product-testimonials
├── .product-testimonials__header
└── .product-testimonials__grid
    └── .product-testimonials__card (block)
        ├── .product-testimonials__photo
        ├── .product-testimonials__stars
        ├── .product-testimonials__quote
        └── .product-testimonials__name
```

### 6.2 Block: `testimonial`

```json
{
  "type": "testimonial",
  "name": "Testimonial",
  "limit": 12,
  "settings": [
    { "type": "image_picker", "id": "photo", "label": "Customer photo" },
    { "type": "text", "id": "name", "label": "Customer name" },
    {
      "type": "range",
      "id": "stars",
      "min": 1,
      "max": 5,
      "default": 5,
      "label": "Rating"
    },
    { "type": "richtext", "id": "quote", "label": "Quote" }
  ]
}
```

### 6.3 Mobile Carousel

Vanilla JS slider (no library). Uses `scroll-snap-type: x mandatory` CSS.

```javascript
class TestimonialsSlider extends HTMLElement {
  constructor() {
    super();
    this.#bindArrows();
  }
  #bindArrows() {
    this.querySelector("[data-next]")?.addEventListener("click", () =>
      this.#scroll(1),
    );
    this.querySelector("[data-prev]")?.addEventListener("click", () =>
      this.#scroll(-1),
    );
  }
  #scroll(dir) {
    const track = this.querySelector(".product-testimonials__track");
    const card = track.querySelector(".product-testimonials__card");
    track.scrollBy({ left: dir * card.offsetWidth, behavior: "smooth" });
  }
}
customElements.define("testimonials-slider", TestimonialsSlider);
```

### 6.4 @app Block Slot

Include `@app` to allow review apps (Judge.me, Okendo, Loox) to inject their widget between blocks.

---

## Phase 7 — Expert / Clinician Panel (0.5 hr)

**File:** `sections/product-expert.liquid`
**CSS:** `assets/product-expert.css`

### 7.1 Layout

Dark green or cream background. Expert headshot left, quote + credentials right.

```
.product-expert
├── .product-expert__photo  ← image_picker
└── .product-expert__content
    ├── .product-expert__quote   (richtext)
    ├── .product-expert__name    (text)
    ├── .product-expert__title   (text)
    └── .product-expert__badge   (image_picker — e.g. Clinician Choice seal)
```

### 7.2 Schema Settings

| Setting            | Type         |
| ------------------ | ------------ |
| `photo`            | image_picker |
| `quote`            | richtext     |
| `expert_name`      | text         |
| `expert_title`     | text         |
| `badge_image`      | image_picker |
| `review_count`     | number       |
| `review_link`      | url          |
| `background_color` | color        |

---

## Phase 8 — FAQ Section (0.5 hr)

**File:** `sections/product-faq.liquid`
**CSS:** `assets/product-faq.css`

### 8.1 Implementation

Use native `<details>`/`<summary>` for accordion — zero JS required:

```liquid
{% for block in section.blocks %}
  {% if block.type == 'faq_item' %}
    <details class="product-faq__item" {{ block.shopify_attributes }}>
      <summary class="product-faq__question">
        {{ block.settings.question }}
        <span class="product-faq__icon" aria-hidden="true">+</span>
      </summary>
      <div class="product-faq__answer">
        {{ block.settings.answer }}
      </div>
    </details>
  {% endif %}
{% endfor %}
```

CSS `-` to `+` toggle via `details[open] .product-faq__icon`.

### 8.2 Block: `faq_item`

```json
{
  "type": "faq_item",
  "name": "FAQ Item",
  "settings": [
    { "type": "text", "id": "question", "label": "Question" },
    { "type": "richtext", "id": "answer", "label": "Answer" }
  ]
}
```

---

## Phase 9 — Guarantee / Subscription Strip (0.25 hr)

**File:** `sections/product-guarantee.liquid`
**CSS:** `assets/product-guarantee.css`

### 9.1 Layout

Full-width dark band. Trust icons (shield, leaf, recycle). "Refills every 8 weeks · Stop or Cancel Anytime."

Blocks for icon+text pairs (`guarantee_item`):

```json
{
  "type": "guarantee_item",
  "name": "Guarantee Item",

  "settings": [
    { "type": "image_picker", "id": "icon", "label": "Icon" },
    { "type": "text", "id": "text", "label": "Text" }
  ]
}
```

---

## Phase 10 — Templates Assembly (0.5 hr)

**File:** `templates/product.json`

Update the product template to register all new sections in the correct order:

```json
{
  "sections": {
    "product-hero": {
      "type": "product-hero",
      "blocks": { ... },
      "block_order": [ ... ]
    },
    "product-benefits": { "type": "product-benefits" },
    "product-education": { "type": "product-education" },
    "product-ingredients": { "type": "product-ingredients" },
    "product-stats": { "type": "product-stats" },
    "product-testimonials": { "type": "product-testimonials" },
    "product-expert": { "type": "product-expert" },
    "product-faq": { "type": "product-faq" },
    "product-guarantee": { "type": "product-guarantee" }
  },
  "order": [
    "product-hero",
    "product-benefits",
    "product-education",
    "product-ingredients",
    "product-stats",
    "product-testimonials",
    "product-expert",
    "product-faq",
    "product-guarantee"
  ]
}
```

---

## Phase 11 — Locales (0.25 hr)

All merchant-visible strings must have translation keys. Add to `locales/en.default.json`:

```json
{
  "sections": {
    "product_hero": {
      "add_to_cart": "Add To Cart",
      "delivery_prefix": "Delivered on",
      "delivery_suffix": "with Express Shipping",
      "assurance": "Refills Ship Every 8 Weeks | Stop or Cancel Anytime"
    },
    "product_faq": {
      "heading": "Frequently Asked Questions"
    }
  }
}
```

---

## Phase 12 — QA & Verification (0.5 hr)

### 12.1 Checklist

| Test                                             | Pass Condition                                                |
| ------------------------------------------------ | ------------------------------------------------------------- |
| Kaching Bundle app block visible in Theme Editor | Merchant can drag-and-drop it into product-hero               |
| Other @app blocks drop zone appears              | Judge.me / Loox / Okendo can be added to testimonials section |
| Mobile layout renders correctly                  | All sections stack single-column, no overflow                 |
| No hardcoded text                                | All strings editable via Theme Editor                         |
| Images via Shopify CDN                           | No external URLs; all `image_url` filtered                    |
| `<details>` FAQ works without JS                 | Accordion opens/closes on click                               |
| Delivery date JS non-blocking                    | Page renders even if JS errors out                            |
| Metafield fallback in hero                       | "Nutritional Information" dialog has graceful empty state     |

### 12.2 Shopify Theme Check

```bash
# Run Shopify CLI theme check
shopify theme check --path .
```

Fix any schema warnings before pushing.

### 12.3 Accessibility Pass

- All images have `alt` attributes (pulled from Shopify media alt text)
- Interactive elements have `:focus-visible` styles
- Stars rendered as `aria-label="4.8 out of 5 stars"`
- FAQ `<details>` is keyboard-navigable natively

---

## Deliverables Summary

| Phase            | Files                                                                                                       | Est. Time    |
| ---------------- | ----------------------------------------------------------------------------------------------------------- | ------------ |
| 0 — Setup        | `snippets/product-theme-vars.liquid`, `layout/theme.liquid` patch                                           | 0.5 hr       |
| 1 — Hero         | `sections/product-hero.liquid`, `assets/product-hero.css`, `assets/product-hero.js`                         | 2 hr         |
| 2 — Benefits     | `sections/product-benefits.liquid`, `assets/product-benefits.css`                                           | 0.5 hr       |
| 3 — Education    | `sections/product-education.liquid`, `assets/product-education.css`                                         | 1 hr         |
| 4 — Ingredients  | `sections/product-ingredients.liquid`, `assets/product-ingredients.css`                                     | 0.75 hr      |
| 5 — Stats        | `sections/product-stats.liquid`, `assets/product-stats.css`                                                 | 0.5 hr       |
| 6 — Testimonials | `sections/product-testimonials.liquid`, `assets/product-testimonials.css`, `assets/product-testimonials.js` | 1 hr         |
| 7 — Expert       | `sections/product-expert.liquid`, `assets/product-expert.css`                                               | 0.5 hr       |
| 8 — FAQ          | `sections/product-faq.liquid`, `assets/product-faq.css`                                                     | 0.5 hr       |
| 9 — Guarantee    | `sections/product-guarantee.liquid`, `assets/product-guarantee.css`                                         | 0.25 hr      |
| 10 — Templates   | `templates/product.json`                                                                                    | 0.5 hr       |
| 11 — Locales     | `locales/en.default.json`                                                                                   | 0.25 hr      |
| 12 — QA          | Theme check, a11y, mobile review                                                                            | 0.5 hr       |
| **Total**        |                                                                                                             | **~8.75 hr** |

---

## 3rd-Party App Integration Guide

Every section exposes at minimum one `"type": "@app"` block slot. This is the standard Shopify mechanism for apps to inject content via the Theme Editor.

### Supported App Positions

| App                          | Recommended Section       | Position                            |
| ---------------------------- | ------------------------- | ----------------------------------- |
| **Kaching Bundles**          | `product-hero`            | After trust icons, before CTA       |
| **Judge.me / Okendo / Loox** | `product-testimonials`    | Top of testimonials section         |
| **Rebuy / LimeSpot**         | Below `product-guarantee` | As separate `@app` section          |
| **Stamped.io**               | `product-testimonials`    | Can coexist with testimonial blocks |
| **Gorgias Chat**             | Any section footer slot   | Use section footer @app slot        |

### Enabling App Blocks (Merchant Steps)

1. In Shopify Admin → Online Store → Themes → Customize
2. Navigate to the product page
3. Click into the desired section (e.g., "Product Hero")
4. Scroll to the block list → click **Add block** → select the app block from the list
5. Drag to reorder relative to native blocks

> **Note:** App block slots are zero-cost to the theme — they only render if the merchant has installed the app and added its block.

---

_Document last updated: 2026-03-04_
_Reference: trysculptique.com/products/lymph-cc-select_

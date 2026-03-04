{%- comment -%}
  ============================================================
  APP PLACEHOLDER TEMPLATE
  ============================================================
  Skill: app_placeholder_generator
  Version: 1.0
  Usage: Replace detected third-party app sections with this
         merchant-editable placeholder.

  Template variables (resolved by App Detection Agent output):
    {{APP_NAME}}             — Human-readable app name
    {{APP_SLUG}}             — URL-safe identifier (e.g. "judge-me")
    {{SECTION_ID}}           — Unique section identifier (e.g. "reviews")
    {{PLACEHOLDER_TYPE}}     — reviews | bundle | upsell | loyalty | quiz | subscription | generic
    {{MERCHANT_INSTRUCTION}} — Plain-English setup instruction for the merchant
    {{APP_STORE_URL}}        — Shopify App Store URL (or empty string if unknown)
    {{DETECTION_CONFIDENCE}} — Float 0.0–1.0 (for audit trail, not shown to merchants)
  ============================================================
{%- endcomment -%}

{%- if section.settings.placeholder_visible -%}
  <div
    class="app-placeholder app-placeholder--{{PLACEHOLDER_TYPE}} section-{{ section.id }}"
    data-app-slug="{{APP_SLUG}}"
    data-app-type="{{PLACEHOLDER_TYPE}}"
  >
    <div class="app-placeholder__inner page-width">
      <div class="app-placeholder__icon" aria-hidden="true">
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="40" height="40" rx="8" fill="currentColor" fill-opacity="0.08"/>
          <path d="M20 10v20M10 20h20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <p class="app-placeholder__name">{{ section.settings.placeholder_label }}</p>
      <p class="app-placeholder__instruction">{{ section.settings.merchant_instruction }}</p>
      {%- if section.settings.app_store_url != blank -%}
        <a
          href="{{ section.settings.app_store_url }}"
          class="app-placeholder__link button button--secondary"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="{{ 'general.accessibility.external_link' | t: label: section.settings.placeholder_label }}"
        >
          {{ 'sections.app_placeholder.install_app' | t }}
        </a>
      {%- endif -%}
    </div>
  </div>
{%- endif -%}

{% style %}
  .section-{{ section.id }}.app-placeholder {
    padding-top: {{ section.settings.padding_top }}px;
    padding-bottom: {{ section.settings.padding_bottom }}px;
  }
{% endstyle %}

{% schema %}
{
  "name": "{{APP_NAME}} (Placeholder)",
  "tag": "section",
  "class": "app-placeholder-section app-placeholder--{{APP_SLUG}}",
  "disabled_on": {
    "groups": ["header", "footer"]
  },
  "settings": [
    {
      "type": "header",
      "content": "App Setup"
    },
    {
      "type": "checkbox",
      "id": "placeholder_visible",
      "label": "Show placeholder in Theme Editor",
      "default": true,
      "info": "Disable this after you have installed and configured the app. The section will remain in your template for the app to inject its content."
    },
    {
      "type": "text",
      "id": "placeholder_label",
      "label": "Section label",
      "default": "{{APP_NAME}}",
      "info": "Displayed only when the placeholder is visible."
    },
    {
      "type": "textarea",
      "id": "merchant_instruction",
      "label": "Setup instructions",
      "default": "{{MERCHANT_INSTRUCTION}}"
    },
    {
      "type": "url",
      "id": "app_store_url",
      "label": "App Store URL",
      "info": "Optional link to the app's Shopify App Store listing."
    },
    {
      "type": "header",
      "content": "Spacing"
    },
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
  ],
  "presets": [
    {
      "name": "{{APP_NAME}} Placeholder",
      "settings": {
        "app_store_url": "{{APP_STORE_URL}}"
      }
    }
  ]
}
{% endschema %}

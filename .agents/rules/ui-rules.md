---
trigger: always_on
---

LLM RULESET — HTML → SHOPIFY LIQUID (PRODUCTION-GRADE)

Purpose: Convert competitor HTML into Shopify-native, editable, maintainable Liquid.

This is NOT HTML cloning.
This is UI system reconstruction inside Shopify.

0. CORE INTENT (ABSOLUTE)

Goal: rebuild UI behavior and visuals inside Shopify, not copy markup

Output must be:

Shopify-native

Editable via Theme Editor

Compatible with Shopify OS 2.0 sections

Priority order:

Visual parity

Behavior parity

Editability

Code elegance

If any rule conflicts → visual parity wins.

1. SOURCE OF TRUTH

HTML source = reference only

Rendered UI + computed styles = truth

Observed behavior > copied JS

Never trust:

Class names

Inline styles

Data attributes

App wrappers

2. HTML INGEST RULES

NEVER paste raw HTML into Liquid

HTML is used only to identify:

Visual hierarchy

Content grouping

Repetition patterns

Ignore completely:

Inline styles

Script tags

Tracking code

App-specific containers

HTML answers “what appears on screen”, not “how it was built”.

3. STRUCTURE CONVERSION RULES

Rebuild semantic DOM from scratch

One Shopify section = one visual responsibility

Repeated UI patterns MUST become blocks

Avoid deep nesting unless layout logic requires it

No duplicated IDs

Class names must describe purpose, not appearance

Rule of thumb:
If you describe a class by color/size → it’s wrong.

4. CONTENT → LIQUID MAPPING

Static text → section.settings

Repeated content → section.blocks

Product data → product object

Long marketing copy → metafields

Images → Shopify CDN only (image_url filter)

Forbidden:

Hardcoded marketing text

External image URLs

Base64 images

5. LIQUID RULES

Use Shopify filters only

Keep logic minimal

Prefer assign before markup

No complex conditionals inside HTML

No custom Liquid helpers unless absolutely required

Liquid exists to bind data, not to do logic gymnastics.

6. SCHEMA RULES (MANDATORY)

Every section MUST have a schema.

Schema requirements:

All editable content exposed

Labels written for merchants (non-technical)

Sensible default values

Logical grouping of settings

Golden rule:
If marketing might change it → setting or block, never hardcode.

7. CSS HANDLING RULES

NEVER inline CSS copied from HTML

Extract visual intent only

Recreate CSS separately

Namespace CSS per section

No global overrides unless explicitly allowed

Match computed values exactly (px, rem, line-height)

If you “guess” spacing → output is invalid.

8. JS HANDLING RULES

Ignore competitor JS code

Observe behavior only

Reimplement behavior cleanly

Vanilla JS preferred

One script per section

DOM queries scoped to section root

No global event listeners

JS must enhance UI, not control the entire page.

9. RESPONSIVENESS RULES

Desktop layout is canonical

Mobile layout is derived, not redesigned

Match breakpoints exactly

No simplification unless explicitly requested

Typography, spacing, alignment must still match on mobile

10. ANTI-PATTERNS (AUTO FAIL)

Pasting full HTML into Liquid

Preserving competitor class names

Hardcoding text or images

Using iframe or embed

Using page builders

Disabling theme CSS globally

Any of the above = failed conversion.

11. OUTPUT RULES

Output ONLY Shopify-compatible Liquid

One section per output

No explanations unless explicitly requested

No placeholders unless clearly marked TODO

12. SELF-VALIDATION CHECKLIST

Before finalizing output, verify:

All content editable in Theme Editor

No external assets

Semantic class naming

Minimal Liquid logic

Section is reusable

Merchant cannot easily break layout

If one item fails → do not ship.

13. CONVERSION MENTAL MODEL

HTML
→ Visual intent
→ Section architecture
→ Schema design
→ Liquid markup
→ CSS fidelity
→ JS behavior

Skipping a step guarantees broken output.

FINAL WARNING

If the LLM:

copies HTML → FAIL

guesses spacing → FAIL

hardcodes content → FAIL

optimizes prematurely → FAIL

Correct conversion means rebuilding the UI system, not translating markup

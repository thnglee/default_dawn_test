"""
Anthropic API wrapper.
All Claude calls go through here — text, vision, JSON parsing.
"""

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

import anthropic

from config import MODEL_DEFAULT, MODEL_SECTION_CONVERT

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


# ── helpers ──────────────────────────────────────────────────────────────────

def _encode_image(path: Path) -> str:
    """Return base64-encoded PNG/JPEG."""
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def _image_block(path: Path) -> dict:
    suffix = path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": _encode_image(path),
        },
    }


def _extract_json(text: str) -> Any:
    """Pull first JSON object or array out of a string."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find first { or [
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        idx = text.find(start_char)
        if idx == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i, ch in enumerate(text[idx:], start=idx):
            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
            elif not in_string:
                if ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[idx: i + 1])
                        except json.JSONDecodeError:
                            break
    raise ValueError(f"No valid JSON found in response:\n{text[:300]}")


# ── core call ─────────────────────────────────────────────────────────────────

def call(
    system: str,
    user_content: list[dict] | str,
    *,
    model: str = MODEL_DEFAULT,
    max_tokens: int = 4096,
    use_thinking: bool = False,
    retries: int = 3,
) -> str:
    """
    Make a single Claude API call and return the full text response.

    For large outputs (section_conversion), streaming is used internally
    via .stream() + .get_final_message() to avoid HTTP timeouts.
    """
    client = _get_client()

    if isinstance(user_content, str):
        user_content = [{"type": "text", "text": user_content}]

    messages = [{"role": "user", "content": user_content}]

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }

    if use_thinking:
        kwargs["thinking"] = {"type": "adaptive"}

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            if max_tokens >= 2048:
                # Use streaming to avoid HTTP timeouts on large outputs
                with client.messages.stream(**kwargs) as stream:
                    final = stream.get_final_message()
            else:
                final = client.messages.create(**kwargs)

            # Collect text blocks (skip thinking blocks)
            parts = [
                block.text
                for block in final.content
                if block.type == "text"
            ]
            return "\n".join(parts)

        except anthropic.RateLimitError as e:
            wait = int(e.response.headers.get("retry-after", "60"))
            time.sleep(wait)
            last_exc = e
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                time.sleep(10 * (attempt + 1))
                last_exc = e
            else:
                raise
        except anthropic.APIConnectionError as e:
            time.sleep(5 * (attempt + 1))
            last_exc = e

    raise RuntimeError(f"LLM call failed after {retries} retries") from last_exc


def call_json(
    system: str,
    user_content: list[dict] | str,
    *,
    model: str = MODEL_DEFAULT,
    max_tokens: int = 2048,
    use_thinking: bool = False,
) -> Any:
    """Call Claude and parse the response as JSON."""
    text = call(
        system,
        user_content,
        model=model,
        max_tokens=max_tokens,
        use_thinking=use_thinking,
    )
    return _extract_json(text)


def call_vision_json(
    system: str,
    text_prompt: str,
    image_paths: list[Path],
    *,
    model: str = MODEL_DEFAULT,
    max_tokens: int = 2048,
) -> Any:
    """
    Vision call with one or more images + a text prompt.
    Returns parsed JSON.
    """
    content: list[dict] = []
    for img_path in image_paths:
        content.append(_image_block(img_path))
    content.append({"type": "text", "text": text_prompt})

    return call_json(system, content, model=model, max_tokens=max_tokens)


def call_section_conversion(
    system: str,
    user_payload: dict,
) -> str:
    """
    Section conversion call — returns raw Liquid file string (not JSON).
    Uses section-conversion model with large token budget.
    """
    user_text = json.dumps(user_payload, indent=2)
    return call(
        system,
        user_text,
        model=MODEL_SECTION_CONVERT,
        max_tokens=6000,
        use_thinking=True,
    )

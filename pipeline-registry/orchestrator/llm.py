"""
LLM wrapper — two backends:
  • OpenAI (gpt-4o) for vision tasks  (call_vision_json)
  • Claude Code CLI for text/JSON/code (call, call_json, call_section_conversion)
"""

import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import openai

from config import MODEL_VISION, OPENAI_API_KEY

_oa_client: openai.OpenAI | None = None


def _get_openai() -> openai.OpenAI:
    global _oa_client
    if _oa_client is None:
        _oa_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    return _oa_client


# ── helpers ──────────────────────────────────────────────────────────────────

def _encode_image(path: Path) -> str:
    """Return base64-encoded PNG/JPEG."""
    return base64.standard_b64encode(path.read_bytes()).decode("utf-8")


def _image_data_url(path: Path) -> str:
    suffix = path.suffix.lower()
    media_type = "image/png" if suffix == ".png" else "image/jpeg"
    return f"data:{media_type};base64,{_encode_image(path)}"


def _extract_json(text: str) -> Any:
    """Pull first JSON object or array out of a string."""
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


# ── OpenAI vision backend ────────────────────────────────────────────────────

def call_vision_json(
    system: str,
    text_prompt: str,
    image_paths: list[Path],
    *,
    max_tokens: int = 2048,
    retries: int = 3,
) -> Any:
    """
    Vision call with one or more images + a text prompt via OpenAI gpt-4o.
    Returns parsed JSON.
    """
    client = _get_openai()

    # Build user message content: images then text
    content: list[dict] = []
    for img_path in image_paths:
        content.append({
            "type": "image_url",
            "image_url": {"url": _image_data_url(img_path), "detail": "high"},
        })
    content.append({"type": "text", "text": text_prompt})

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL_VISION,
                messages=messages,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            text = resp.choices[0].message.content or ""
            return _extract_json(text)

        except openai.RateLimitError as e:
            wait = 60
            print(f"  ⚠ OpenAI rate limit, waiting {wait}s (attempt {attempt + 1})")
            time.sleep(wait)
            last_exc = e
        except openai.APIStatusError as e:
            if e.status_code >= 500:
                time.sleep(10 * (attempt + 1))
                last_exc = e
            else:
                raise
        except openai.APIConnectionError as e:
            time.sleep(5 * (attempt + 1))
            last_exc = e

    raise RuntimeError(f"OpenAI vision call failed after {retries} retries") from last_exc


# ── Claude Code CLI backend ──────────────────────────────────────────────────

def _claude_cli(
    system: str,
    user_text: str,
    *,
    retries: int = 3,
) -> str:
    """
    Call `claude --print` via subprocess.
    System prompt via --system-prompt flag (or temp file if >100KB).
    User content piped via stdin.
    """
    last_exc: Exception | None = None

    # Strip env vars that prevent nested Claude sessions
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDECODE")}

    for attempt in range(retries):
        cmd = ["claude", "--print", "--max-turns", "5", "--verbose"]
        tmp_file = None

        try:
            # System prompt: flag for short, temp file for long
            if len(system.encode("utf-8")) > 100_000:
                tmp_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False
                )
                tmp_file.write(system)
                tmp_file.flush()
                cmd += ["--system-prompt", f"$(cat {tmp_file.name})"]
            else:
                cmd += ["--system-prompt", system]

            result = subprocess.run(
                cmd,
                input=user_text,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )

            if result.returncode == 0:
                return result.stdout.strip()

            stderr = result.stderr.strip()
            print(f"  ⚠ Claude CLI exit code {result.returncode} (attempt {attempt + 1}): {stderr[:200]}")
            last_exc = RuntimeError(f"claude exit {result.returncode}: {stderr[:200]}")
            time.sleep(5 * (attempt + 1))

        except subprocess.TimeoutExpired as e:
            print(f"  ⚠ Claude CLI timeout (attempt {attempt + 1})")
            last_exc = e
            time.sleep(5 * (attempt + 1))
        finally:
            if tmp_file is not None:
                Path(tmp_file.name).unlink(missing_ok=True)

    raise RuntimeError(f"Claude CLI call failed after {retries} retries") from last_exc


def call(
    system: str,
    user_content: str,
    *,
    max_tokens: int = 4096,
    retries: int = 3,
) -> str:
    """
    Make a Claude Code CLI call and return the full text response.
    max_tokens is accepted for API compatibility but not used by CLI.
    """
    return _claude_cli(system, user_content, retries=retries)


def call_json(
    system: str,
    user_content: str,
    *,
    max_tokens: int = 2048,
) -> Any:
    """Call Claude CLI and parse the response as JSON."""
    text = call(system, user_content, max_tokens=max_tokens)
    return _extract_json(text)


def call_section_conversion(
    system: str,
    user_payload: dict,
) -> str:
    """
    Section conversion call — returns raw Liquid file string (not JSON).
    Uses Claude Code CLI.
    """
    user_text = json.dumps(user_payload, indent=2)
    return call(system, user_text, max_tokens=6000)

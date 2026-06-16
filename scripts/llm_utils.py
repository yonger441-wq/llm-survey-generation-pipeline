import http.client
import json
import os
import re
import time
from pathlib import Path
from urllib import error, request

# Load .env file from project root on import
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Project root: two levels up from this script (scripts/llm_utils.py → root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config(path: str | Path | None = None) -> dict:
    """Load pipeline_config.json. If *path* is None, looks in config/ under
    the project root."""
    if path is None:
        path = PROJECT_ROOT / "config" / "pipeline_config.json"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def resolve_path(cfg: dict, key: str) -> Path:
    """Resolve a config path value relative to PROJECT_ROOT."""
    return PROJECT_ROOT / cfg[key]


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def load_prompt(template_name: str, prompts_dir: str | Path | None = None) -> str:
    """Load a prompt .md file from the prompts directory.

    *template_name* can be with or without .md extension.
    """
    if prompts_dir is None:
        prompts_dir = PROJECT_ROOT / "prompts"
    prompts_dir = Path(prompts_dir)
    if not template_name.endswith(".md"):
        template_name += ".md"
    path = prompts_dir / template_name
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return read_text(path)


def render_prompt(template: str, replacements: dict[str, str]) -> str:
    """Replace {{VAR}} placeholders in a template string."""
    result = template
    for key, value in replacements.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def render_prompt_file(template_name: str, replacements: dict[str, str],
                       prompts_dir: str | Path | None = None) -> str:
    """Load a prompt file and render its placeholders in one call."""
    template = load_prompt(template_name, prompts_dir)
    return render_prompt(template, replacements)


# ---------------------------------------------------------------------------
# LLM API calls
# ---------------------------------------------------------------------------

def call_chat_api(base_url: str, api_key: str, model: str, messages: list,
                  timeout: int = 300, retries: int = 3,
                  temperature: float = 0.2, max_tokens: int = 8192) -> str:
    """Call an OpenAI-compatible chat completion API."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    last_error = None
    total_attempts = max(retries, 1)
    for attempt in range(total_attempts):
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                try:
                    raw = resp.read()
                except http.client.IncompleteRead as exc:
                    raw = exc.partial
                data = json.loads(raw.decode("utf-8"))
            break
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"API request failed: HTTP {exc.code} {body}") from exc
        except error.URLError as exc:
            last_error = RuntimeError(f"API request failed: {exc.reason}")
        except (http.client.IncompleteRead, json.JSONDecodeError) as exc:
            last_error = RuntimeError(f"API response was incomplete or invalid JSON: {exc}")
        if attempt < total_attempts - 1:
            time.sleep(min(30, 5 * (attempt + 1)))
    else:
        raise last_error if last_error else RuntimeError("API request failed for an unknown reason.")

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected API response: {json.dumps(data, ensure_ascii=False)}") from exc


def call_ollama_generate(ollama_url: str, model: str, prompt: str,
                         timeout: int = 1800) -> str:
    """Call Ollama generate API."""
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    req = request.Request(
        ollama_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if "response" not in data:
        raise RuntimeError("Ollama API returned no response field.")
    return str(data["response"]).strip()


# ---------------------------------------------------------------------------
# High-level LLM call — reads config, handles env vars, rate limiting
# ---------------------------------------------------------------------------

_last_call_time: float = 0.0


def call_llm(prompt: str, cfg: dict | None = None, system: str = "",
             model: str | None = None) -> str:
    """Make a single LLM call using config settings.

    Handles API key from env var, rate limiting, and retries.
    """
    if cfg is None:
        cfg = load_config()

    llm_cfg = cfg["llm"]
    provider = llm_cfg["provider"]
    use_model = model or llm_cfg["model"]

    # Rate limiting
    global _last_call_time
    min_interval = 60.0 / llm_cfg.get("rate_limit_rpm", 30)
    elapsed = time.time() - _last_call_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if provider == "deepseek":
        api_key = os.environ.get(llm_cfg["api_key_env"], "")
        if not api_key:
            raise EnvironmentError(f"Env var {llm_cfg['api_key_env']} not set")
        result = call_chat_api(
            base_url=llm_cfg["base_url"],
            api_key=api_key,
            model=use_model,
            messages=messages,
            timeout=llm_cfg.get("timeout", 300),
            retries=llm_cfg.get("max_retries", 3),
            temperature=llm_cfg.get("temperature", 0.2),
            max_tokens=llm_cfg.get("max_tokens", 8192),
        )
    elif provider == "ollama":
        result = call_ollama_generate(
            ollama_url="http://localhost:11434/api/generate",
            model=use_model,
            prompt=prompt,
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    _last_call_time = time.time()
    return result


# ---------------------------------------------------------------------------
# JSON extraction from LLM responses
# ---------------------------------------------------------------------------

def extract_json(text: str) -> str:
    """Extract the first JSON object or array from LLM output text."""
    # Try to find ```json ... ``` blocks first
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try to find raw JSON
    for start_char, end_char in [("[", "]"), ("{", "}")]:
        start = text.find(start_char)
        if start >= 0:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    raise ValueError("No JSON found in LLM response")

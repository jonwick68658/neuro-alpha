# model_services.py

import os
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator, Protocol, runtime_checkable

# Optional: integrate per-user API keys via Secrets Vault.
# If you want per-user routing (recommended), set USE_VAULT_KEYS=true and pass user_id to methods.
@runtime_checkable
class VaultLike(Protocol):
    def get_secret(self, user_id: str, secret_type: str, secret_name: str) -> Optional[str]:
        ...


try:
    from secrets_vault import vault as _vault  # type: ignore
    HAVE_VAULT = True
    vault: Optional[VaultLike] = _vault  # precise type for Pylance
except Exception:
    HAVE_VAULT = False
    vault = None  # Explicit Optional[VaultLike]

# -----------------------------------------------------------------------------------
# Environment and constants
# -----------------------------------------------------------------------------------

# Server-level fallback API key (used if user-level key not found or disabled).
OPENROUTER_API_KEY = (
    os.getenv("OPENROUTER_API_KEY")
    or os.getenv("OPEN_ROUTER_KEY")
    or os.getenv("OPEN_ROUTER_API_KEY")
    or ""
)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Timeout guidance: non-streaming requests finish within DEFAULT_TIMEOUT.
# Streaming keeps the connection open; set timeout=None when streaming.
DEFAULT_TIMEOUT = float(os.getenv("OPENROUTER_TIMEOUT_SEC", "60"))

# Optional provider preferences for OpenRouter routing.
# Example JSON (set via env OPENROUTER_PROVIDER_PREFS_JSON):
#   {"order": ["OpenAI", "Anthropic"], "allow_fallbacks": true}
PROVIDER_PREFS_ENV = os.getenv("OPENROUTER_PROVIDER_PREFS_JSON", "").strip()
try:
    PROVIDER_PREFS: Optional[Dict[str, Any]] = json.loads(PROVIDER_PREFS_ENV) if PROVIDER_PREFS_ENV else None
except json.JSONDecodeError:
    PROVIDER_PREFS = None

# Whether to attempt per-user OpenRouter routing via Secrets Vault.
USE_VAULT_KEYS = os.getenv("USE_VAULT_KEYS", "false").lower() in ("1", "true", "yes")

# -----------------------------------------------------------------------------------
# Model registry and tiering (for main.py endpoints)
# -----------------------------------------------------------------------------------

MODEL_REGISTRY: List[Dict[str, Any]] = [
    # Free options
    {"id": "meta-llama/llama-3.2-3b-instruct:free", "name": "Llama 3.2 3B (Free)", "tier": "free"},
    {"id": "google/gemini-2.0-flash-001:free", "name": "Gemini 2.0 Flash (Free)", "tier": "free"},
    # OpenRouter standard (requires OpenRouter key; can be server-level or user-level)
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o mini", "tier": "openrouter"},
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "tier": "openrouter"},
    {"id": "mistralai/mistral-small-3.2-24b-instruct", "name": "Mistral Small 24B", "tier": "openrouter"},
    # OpenAI direct (still routed via OpenRouter if using their endpoint)
    {"id": "openai/gpt-4o", "name": "GPT-4o", "tier": "openai"},
    # Premium bucket (users with both keys or explicit allow-list)
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat", "tier": "premium"},
]


def get_model_tier(model_id: str) -> str:
    for m in MODEL_REGISTRY:
        if m.get("id") == model_id:
            return m.get("tier", "free")
    return "free"


def filter_models_by_tier(models: List[Dict[str, Any]], user_tier: str) -> List[Dict[str, Any]]:
    if user_tier == "premium":
        return models
    if user_tier == "openrouter":
        return [m for m in models if m.get("tier") in ("free", "openrouter")]
    if user_tier == "openai":
        return [m for m in models if m.get("tier") in ("free", "openai")]
    return [m for m in models if m.get("tier") == "free"]

# -----------------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------------


def _resolve_openrouter_key(user_id: Optional[str]) -> str:
    """
    Resolve the API key to use.
    Priority (if USE_VAULT_KEYS=True and vault available):
      1) User-specific key in vault under ('api_key', 'openrouter')
      2) Server-level fallback OPENROUTER_API_KEY
    If USE_VAULT_KEYS=False or vault unavailable, returns OPENROUTER_API_KEY.
    """
    if USE_VAULT_KEYS and HAVE_VAULT and vault is not None and user_id:
        try:
            key = vault.get_secret(user_id, 'api_key', 'openrouter')
            if key and key.strip():
                return key.strip()
        except Exception:
            # fall back to server-level
            pass
    return OPENROUTER_API_KEY


async def _with_backoff(coro_factory, retries: int = 3, base_delay: float = 0.8, factor: float = 2.0, max_delay: float = 8.0):
    for attempt in range(retries):
        try:
            return await coro_factory()
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            delay = min(base_delay * (factor ** attempt), max_delay)
            print(f"[ModelService] transient error: {e}; retry {attempt+1}/{retries} in {delay:.2f}s")
            await asyncio.sleep(delay)
    # Final attempt without catching to bubble up
    return await coro_factory()

# -----------------------------------------------------------------------------------
# ModelService
# -----------------------------------------------------------------------------------


class ModelService:
    """
    - chat_completion: non-streaming, returns full text
    - chat_completion_stream: streaming via SSE (OpenRouter). Yields raw chunks; caller parses SSE frames.
    - get_models, get_model_tier, filter_models_by_tier: used by main.py
    """

    def __init__(self):
        pass

    def get_models(self) -> List[Dict[str, Any]]:
        return MODEL_REGISTRY.copy()

    # ---------------- Non-streaming ----------------

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        web_search: bool = False,
        provider_prefs: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> str:
        """
        Sends a non-streaming chat request and returns final content.
        """
        api_key = _resolve_openrouter_key(user_id)
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json",
        }
        if not headers["Authorization"]:
            print("[ModelService] WARNING: No OpenRouter API key configured")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if web_search:
            payload.setdefault("extra_body", {})["web_search"] = True
        if provider_prefs is None:
            provider_prefs = PROVIDER_PREFS
        if provider_prefs:
            payload["provider"] = provider_prefs

        async def _do():
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                r = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
                # OpenRouter-compatible parse
                content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
                return content

        return await _with_backoff(_do)

    # ---------------- Streaming (SSE) ----------------

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        web_search: bool = False,
        provider_prefs: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Async generator yielding SSE text chunks from OpenRouter.

        We stream raw chunks and let the caller (main.py /api/chat-stream)
        manage buffering and parse SSE frames per OpenRouter docs:
        - Lines may be comments starting with ':'
        - Payload lines start with 'data: '
        - '[DONE]' indicates the end

        Docs: https://openrouter.ai/docs/api-reference/streaming
        """
        api_key = _resolve_openrouter_key(user_id)
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)
        if not headers["Authorization"]:
            print("[ModelService] WARNING: No OpenRouter API key configured for streaming")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if web_search:
            payload.setdefault("extra_body", {})["web_search"] = True
        if provider_prefs is None:
            provider_prefs = PROVIDER_PREFS
        if provider_prefs:
            payload["provider"] = provider_prefs

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", OPENROUTER_URL, headers=headers, json=payload) as resp:
                resp.raise_for_status()
                async for raw_chunk in resp.aiter_text():
                    if raw_chunk:
                        yield raw_chunk

# Re-exports for main.py
__all__ = ["ModelService", "get_model_tier", "filter_models_by_tier"]
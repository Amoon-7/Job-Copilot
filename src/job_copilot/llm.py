"""Accès LLM unique (LiteLLM) : JSON structuré validé, suivi coût/latence/tokens."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings
from .observability import setup_observability

T = TypeVar("T", bound=BaseModel)


@dataclass
class UsageTracker:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0

    def snapshot(self) -> dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_s": round(self.latency_s, 2),
        }


_current: ContextVar[UsageTracker | None] = ContextVar("usage_tracker", default=None)


@contextmanager
def track() -> Iterator[UsageTracker]:
    """`with llm.track() as u:` -> u.snapshot() donne coût/latence de tout le bloc."""
    tracker = UsageTracker()
    token = _current.set(tracker)
    try:
        yield tracker
    finally:
        _current.reset(token)


def _record(resp, elapsed: float) -> None:
    tracker = _current.get()
    if tracker is None:
        return
    import litellm

    usage = getattr(resp, "usage", None)
    tracker.calls += 1
    tracker.latency_s += elapsed
    if usage:
        tracker.prompt_tokens += getattr(usage, "prompt_tokens", 0) or 0
        tracker.completion_tokens += getattr(usage, "completion_tokens", 0) or 0
    try:
        tracker.cost_usd += float(litellm.completion_cost(completion_response=resp) or 0.0)
    except Exception:  # modèle inconnu du tableau de prix (ex. modèle local)
        pass


def extract_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Aucun objet JSON dans la réponse du modèle")
    return text[start : end + 1]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def complete_json(
    *,
    system: str,
    user: str,
    schema: type[T],
    model: str | None = None,
    temperature: float = 0.2,
    name: str = "llm_call",
) -> T:
    import litellm

    setup_observability()
    model = model or get_settings().llm_strong_model
    t0 = time.perf_counter()
    resp = litellm.completion(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        response_format={"type": "json_object"},
        metadata={"generation_name": name},
    )
    _record(resp, time.perf_counter() - t0)
    content = resp.choices[0].message.content or ""
    return schema.model_validate(json.loads(extract_json(content)))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    import litellm

    setup_observability()
    resp = litellm.embedding(model=model or get_settings().embed_model, input=texts)
    return [d["embedding"] for d in resp.data]

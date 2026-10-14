"""Traçage Langfuse via les callbacks LiteLLM (no-op si les clés sont absentes)."""

import os

from .config import get_settings

_done = False


def setup_observability() -> None:
    global _done
    if _done:
        return
    _done = True
    import litellm

    litellm.drop_params = True  # ignore les paramètres non supportés par un fournisseur
    s = get_settings()
    if s.langfuse_public_key and s.langfuse_secret_key:
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", s.langfuse_public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", s.langfuse_secret_key)
        os.environ.setdefault("LANGFUSE_HOST", s.langfuse_host)
        litellm.success_callback = ["langfuse"]
        litellm.failure_callback = ["langfuse"]

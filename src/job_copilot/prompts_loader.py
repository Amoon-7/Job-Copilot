"""Prompts versionnés : un fichier .md par prompt, sections séparées par ---USER---."""

import hashlib
from pathlib import Path

from .config import get_settings

_ROOT = Path(__file__).parent / "prompts"


def _path(name: str) -> Path:
    return _ROOT / get_settings().prompt_version / f"{name}.md"


def load_prompt(name: str) -> tuple[str, str]:
    raw = _path(name).read_text(encoding="utf-8")
    system, _, user = raw.partition("---USER---")
    return system.strip(), user.strip()


def prompt_version(name: str) -> str:
    """Identifiant stable : <version>-<hash du contenu>, stocké avec chaque résultat."""
    digest = hashlib.sha1(_path(name).read_bytes()).hexdigest()[:8]
    return f"{get_settings().prompt_version}-{digest}"


def render(template: str, **values: str) -> str:
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    return template

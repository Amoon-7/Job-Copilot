from pathlib import Path

import yaml

from .config import get_settings
from .schemas import CandidateProfile


def load_profile(path: str | None = None) -> CandidateProfile:
    p = Path(path or get_settings().profile_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Profil introuvable : {p}. Copie data/profile.example.yaml vers data/profile.yaml."
        )
    return CandidateProfile.model_validate(yaml.safe_load(p.read_text(encoding="utf-8")))

"""Vérification d'ancrage : LLM (affirmation -> passage du CV) + garde-fou déterministe."""

import re

from .. import llm
from ..config import get_settings
from ..prompts_loader import load_prompt, render
from ..schemas import CandidateProfile, Claim, ClaimExtraction, DraftContent, GroundingReport

_NUMBER = re.compile(r"\d[\d.,]*\s?%?")


def numeric_guard(text: str, allowed_text: str) -> list[Claim]:
    """Tout nombre du texte généré absent du profil ET de l'offre est une invention probable."""
    allowed = allowed_text.replace(" ", "")
    flagged = []
    for m in _NUMBER.finditer(text):
        token = m.group().strip().rstrip(".,")
        if token and token.replace(" ", "") not in allowed:
            flagged.append(
                Claim(
                    text=f"Nombre non présent dans le CV ni l'offre : « {token} »",
                    supported=False,
                    source="guard",
                )
            )
    return flagged


def check_grounding(
    draft: DraftContent,
    profile: CandidateProfile,
    offer_text: str = "",
    model: str | None = None,
) -> GroundingReport:
    system, user = load_prompt("verify")
    extraction = llm.complete_json(
        system=system,
        user=render(user, profile=profile.as_text(), text=draft.as_text()),
        schema=ClaimExtraction,
        model=model or get_settings().llm_strong_model,
        temperature=0.0,
        name="verify",
    )
    valid_ids = set(profile.evidence())
    claims = []
    for c in extraction.claims:
        # Une affirmation « supportée » sans passage valide cité n'est pas supportée.
        if c.supported and not (set(c.evidence_ids) & valid_ids):
            c = c.model_copy(update={"supported": False})
        claims.append(c)
    claims += numeric_guard(draft.as_text(), profile.as_text() + "\n" + offer_text)
    return GroundingReport(claims=claims)

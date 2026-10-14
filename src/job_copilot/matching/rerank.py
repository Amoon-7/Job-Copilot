from .. import llm
from ..config import get_settings
from ..prompts_loader import load_prompt, prompt_version, render
from ..schemas import CandidateProfile, JobOffer, RerankOutput

PROMPT = "rerank"


def rerank(offer: JobOffer, profile: CandidateProfile, model: str | None = None) -> RerankOutput:
    system, user = load_prompt(PROMPT)
    return llm.complete_json(
        system=system,
        user=render(user, profile=profile.as_text(), offer=offer.as_text()[:6000]),
        schema=RerankOutput,
        model=model or get_settings().llm_fast_model,
        temperature=0.0,
        name="rerank",
    )


def version() -> str:
    return prompt_version(PROMPT)

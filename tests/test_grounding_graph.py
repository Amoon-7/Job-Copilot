"""Teste la boucle de correction avec un faux LLM (aucun appel réseau)."""

from job_copilot import llm
from job_copilot.agents.graph import run_agent
from job_copilot.agents.grounding import numeric_guard
from job_copilot.schemas import (
    CandidateProfile,
    Claim,
    ClaimExtraction,
    DraftContent,
    Experience,
    JobOffer,
    OfferAnalysis,
)

PROFILE = CandidateProfile(
    name="Test",
    skills=["Python"],
    experiences=[
        Experience(
            title="Ingénieur IA",
            company="X",
            period="2025",
            bullets=["Déploiement d'un pipeline ML en production."],
        )
    ],
)
OFFER = JobOffer(source_id="1", title="MLOps", company="Acme", description="Python, Docker.")


def test_numeric_guard_flags_invented_numbers_only():
    flagged = numeric_guard("J'ai réduit la latence de 40% sur 2025.", "Profil 2025 offre")
    assert len(flagged) == 1 and "40%" in flagged[0].text


def test_correction_loop_removes_invented_claim(monkeypatch):
    calls = {"generate": 0}

    def fake(*, schema, user, **_):
        if schema is OfferAnalysis:
            return OfferAnalysis(requirements=["Python"])
        if schema is DraftContent:
            calls["generate"] += 1
            if calls["generate"] == 1:
                return DraftContent(cover_letter="J'ai géré 50 serveurs.", cv_highlights=[])
            return DraftContent(cover_letter="J'ai déployé un pipeline ML.", cv_highlights=[])
        if schema is ClaimExtraction:
            if "50 serveurs" in user:
                return ClaimExtraction(claims=[Claim(text="a géré 50 serveurs", supported=False)])
            return ClaimExtraction(
                claims=[Claim(text="a déployé un pipeline ML", evidence_ids=["E2"], supported=True)]
            )
        raise AssertionError(schema)

    monkeypatch.setattr(llm, "complete_json", fake)
    state = run_agent(OFFER, PROFILE, max_attempts=3, threshold=0.0)
    assert state["attempts"] == 2
    assert state["best_report"].unsupported_rate == 0.0
    assert "pipeline" in state["best_draft"].cover_letter


def test_no_loop_when_single_attempt(monkeypatch):
    def fake(*, schema, **_):
        if schema is OfferAnalysis:
            return OfferAnalysis()
        if schema is DraftContent:
            return DraftContent(cover_letter="x", cv_highlights=[])
        return ClaimExtraction(claims=[Claim(text="faux", supported=False)])

    monkeypatch.setattr(llm, "complete_json", fake)
    state = run_agent(OFFER, PROFILE, max_attempts=1)
    assert state["attempts"] == 1 and state["best_report"].unsupported_rate == 1.0

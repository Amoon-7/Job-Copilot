"""Graphe LangGraph : analyse -> génération -> vérification -> (boucle de correction | fin)."""

from typing import TypedDict

from langgraph.graph import END, StateGraph

from .. import llm
from ..config import get_settings
from ..prompts_loader import load_prompt, render
from ..schemas import (
    CandidateProfile,
    DraftContent,
    GroundingReport,
    JobOffer,
    OfferAnalysis,
)
from .grounding import check_grounding


class State(TypedDict, total=False):
    offer: JobOffer
    profile: CandidateProfile
    analysis: OfferAnalysis
    draft: DraftContent
    report: GroundingReport
    best_draft: DraftContent
    best_report: GroundingReport
    feedback: str
    attempts: int
    max_attempts: int
    threshold: float


def analyze_offer(state: State) -> State:
    system, user = load_prompt("analyze_offer")
    analysis = llm.complete_json(
        system=system,
        user=render(user, offer=state["offer"].as_text()[:6000]),
        schema=OfferAnalysis,
        model=get_settings().llm_fast_model,
        name="analyze_offer",
    )
    return {"analysis": analysis, "attempts": 0, "feedback": ""}


def generate(state: State) -> State:
    system, user = load_prompt("generate")
    draft = llm.complete_json(
        system=system,
        user=render(
            user,
            profile=state["profile"].as_text(),
            offer=state["offer"].as_text()[:6000],
            analysis=state["analysis"].model_dump_json(),
            feedback=state.get("feedback", ""),
        ),
        schema=DraftContent,
        model=get_settings().llm_strong_model,
        temperature=0.4,
        name="generate",
    )
    return {"draft": draft, "attempts": state.get("attempts", 0) + 1}


def verify(state: State) -> State:
    report = check_grounding(state["draft"], state["profile"], state["offer"].as_text())
    update: State = {"report": report}
    best = state.get("best_report")
    if best is None or report.unsupported_rate < best.unsupported_rate:
        update["best_draft"], update["best_report"] = state["draft"], report
    bad = [c.text for c in report.unsupported]
    update["feedback"] = (
        "CORRECTION REQUISE — la version précédente contenait des affirmations non supportées "
        "par le profil. Supprime-les ou remplace-les par des faits réels :\n- " + "\n- ".join(bad)
        if bad
        else ""
    )
    return update


def route(state: State) -> str:
    done = state["report"].unsupported_rate <= state.get("threshold", 0.0)
    return "end" if done or state["attempts"] >= state["max_attempts"] else "retry"


def build_graph():
    g = StateGraph(State)
    g.add_node("analyze_offer", analyze_offer)
    g.add_node("generate", generate)
    g.add_node("verify", verify)
    g.set_entry_point("analyze_offer")
    g.add_edge("analyze_offer", "generate")
    g.add_edge("generate", "verify")
    g.add_conditional_edges("verify", route, {"retry": "generate", "end": END})
    return g.compile()


def run_agent(
    offer: JobOffer,
    profile: CandidateProfile,
    max_attempts: int | None = None,
    threshold: float | None = None,
) -> State:
    """max_attempts=1 désactive la boucle de correction (utile pour l'ablation en éval)."""
    s = get_settings()
    return build_graph().invoke(
        {
            "offer": offer,
            "profile": profile,
            "max_attempts": max_attempts or s.max_attempts,
            "threshold": s.grounding_threshold if threshold is None else threshold,
        }
    )

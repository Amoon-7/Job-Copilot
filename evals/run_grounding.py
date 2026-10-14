"""Ablation de fidélité : brouillons SANS boucle de correction (1 essai) vs AVEC (N essais).

Les deux sorties sont jugées par un modèle INDÉPENDANT (EVAL_JUDGE_MODEL), pas par le
vérificateur du pipeline, pour éviter qu'il se note lui-même.

Usage : python -m evals.run_grounding evals/data/offers_labeled.jsonl
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from evals.metrics import mean
from job_copilot import llm
from job_copilot.agents.graph import run_agent
from job_copilot.agents.grounding import check_grounding
from job_copilot.config import get_settings
from job_copilot.profile import load_profile
from job_copilot.schemas import JobOffer


def main(path: str, limit: int = 20) -> None:
    s = get_settings()
    profile = load_profile()
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    results: dict[str, dict[str, list[float]]] = {
        "sans_boucle": {"rate": [], "cost": []},
        "avec_boucle": {"rate": [], "cost": []},
    }
    for r in rows[:limit]:
        offer = JobOffer.model_validate(r["offer"])
        for name, attempts in (("sans_boucle", 1), ("avec_boucle", s.max_attempts)):
            with llm.track() as usage:
                state = run_agent(offer, profile, max_attempts=attempts)
            judged = check_grounding(
                state["best_draft"], profile, offer.as_text(), model=s.eval_judge_model
            )
            results[name]["rate"].append(judged.unsupported_rate)
            results[name]["cost"].append(usage.snapshot()["cost_usd"])
    report = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "n": min(len(rows), limit),
        "judge": s.eval_judge_model,
        "generation_model": s.llm_strong_model,
        **{
            k: {
                "unsupported_rate_moyen": round(mean(v["rate"]), 4),
                "cout_moyen_usd": round(mean(v["cost"]), 5),
            }
            for k, v in results.items()
        },
    }
    out = Path("evals/reports") / f"grounding_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evals/data/offers_labeled.jsonl")

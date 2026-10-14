"""Éval du matching : classe les offres annotées par score LLM, compare à tes labels.

Usage : python -m evals.run_matching evals/data/offers_labeled.jsonl
Labels : 0 = hors sujet, 1 = acceptable, 2 = excellent.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from evals.metrics import mrr, ndcg_at_k, precision_at_k
from job_copilot import llm
from job_copilot.config import get_settings
from job_copilot.matching.rerank import rerank, version
from job_copilot.profile import load_profile
from job_copilot.schemas import JobOffer


def main(path: str) -> None:
    profile = load_profile()
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    scored = []
    with llm.track() as usage:
        for r in rows:
            out = rerank(JobOffer.model_validate(r["offer"]), profile)
            scored.append((out.score, r["label"], r["offer"]["title"]))
    ranked = [label for _, label, _ in sorted(scored, key=lambda x: -x[0])]
    report = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "n": len(rows),
        "model": get_settings().llm_fast_model,
        "prompt_version": version(),
        "precision@5": round(precision_at_k(ranked, 5), 3),
        "mrr": round(mrr(ranked), 3),
        "ndcg@10": round(ndcg_at_k(ranked, 10), 3),
        "usage": usage.snapshot(),
    }
    out_path = Path("evals/reports") / f"matching_{datetime.now():%Y%m%d_%H%M%S}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "evals/data/offers_labeled.jsonl")

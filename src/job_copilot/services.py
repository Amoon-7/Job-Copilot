"""Orchestration du pipeline : ingestion -> embeddings -> matching -> brouillons -> revue."""

from datetime import UTC, datetime

from sqlalchemy import select

from . import llm
from .agents.graph import run_agent
from .config import get_settings
from .db import DraftRow, MatchRow, OfferRow, SessionLocal
from .ingestion.base import Connector
from .ingestion.dedup import dedupe, fingerprint
from .ingestion.france_travail import FranceTravailConnector
from .ingestion.rss import RssConnector
from .matching import rerank as rr
from .profile import load_profile
from .schemas import JobOffer


def build_connectors() -> list[Connector]:
    s = get_settings()
    connectors: list[Connector] = []
    if s.ft_client_id and s.ft_client_secret:
        for kw in s.keywords:
            for dep in s.departments or [None]:
                connectors.append(
                    FranceTravailConnector(s.ft_client_id, s.ft_client_secret, kw, dep)
                )
    connectors += [RssConnector(url) for url in s.feeds]
    return connectors


def to_schema(row: OfferRow) -> JobOffer:
    return JobOffer(
        source=row.source,
        source_id=row.source_id,
        title=row.title,
        company=row.company,
        location=row.location,
        description=row.description,
        url=row.url,
        contract_type=row.contract_type,
        published_at=row.published_at,
    )


def ingest_all() -> dict:
    fetched: list[JobOffer] = []
    errors: list[str] = []
    for c in build_connectors():
        try:
            fetched += c.fetch()
        except Exception as exc:  # une source en panne ne doit pas bloquer les autres
            errors.append(f"{c.name}: {exc}")
    unique = dedupe(fetched)
    inserted = 0
    with SessionLocal() as db:
        known_fp = set(db.scalars(select(OfferRow.fingerprint)))
        known_ids = set(db.execute(select(OfferRow.source, OfferRow.source_id)).all())
        for o in unique:
            fp = fingerprint(o)
            if fp in known_fp or (o.source, o.source_id) in known_ids:
                continue
            db.add(OfferRow(fingerprint=fp, **o.model_dump()))
            known_fp.add(fp)
            inserted += 1
        db.commit()
    return {
        "fetched": len(fetched),
        "after_dedup": len(unique),
        "inserted": inserted,
        "errors": errors,
    }


def embed_pending(batch: int = 32) -> int:
    with SessionLocal() as db:
        rows = db.scalars(select(OfferRow).where(OfferRow.embedding.is_(None))).all()
        for i in range(0, len(rows), batch):
            chunk = rows[i : i + batch]
            vecs = llm.embed([to_schema(r).as_text()[:4000] for r in chunk])
            for r, v in zip(chunk, vecs, strict=True):
                r.embedding = v
        db.commit()
        return len(rows)


def run_matching(top_k: int = 10) -> dict:
    s = get_settings()
    profile = load_profile()
    version = rr.version()
    with llm.track() as usage:
        embedded = embed_pending()
        profile_vec = llm.embed([profile.as_text()])[0]
        with SessionLocal() as db:
            shortlist = db.scalars(
                select(OfferRow)
                .where(OfferRow.embedding.is_not(None))
                .order_by(OfferRow.embedding.cosine_distance(profile_vec))
                .limit(s.shortlist_size)
            ).all()
            done = set(
                db.scalars(select(MatchRow.offer_id).where(MatchRow.prompt_version == version))
            )
            for row in shortlist:
                if row.id in done:
                    continue
                out = rr.rerank(to_schema(row), profile)
                db.add(
                    MatchRow(
                        offer_id=row.id,
                        score=out.score,
                        rationale=out.rationale,
                        strengths=out.strengths,
                        gaps=out.gaps,
                        model=s.llm_fast_model,
                        prompt_version=version,
                    )
                )
            db.commit()
    return {
        "embedded": embedded,
        "shortlisted": len(shortlist),
        "usage": usage.snapshot(),
        "top": list_matches(top_k),
    }


def list_matches(limit: int = 20) -> list[dict]:
    with SessionLocal() as db:
        q = (
            select(MatchRow, OfferRow)
            .join(OfferRow, OfferRow.id == MatchRow.offer_id)
            .order_by(MatchRow.score.desc())
            .limit(limit)
        )
        return [
            {
                "offer_id": o.id,
                "title": o.title,
                "company": o.company,
                "location": o.location,
                "url": o.url,
                "score": m.score,
                "rationale": m.rationale,
                "strengths": m.strengths,
                "gaps": m.gaps,
            }
            for m, o in db.execute(q).all()
        ]


def generate_draft(offer_id: int) -> dict:
    s = get_settings()
    profile = load_profile()
    with SessionLocal() as db:
        row = db.get(OfferRow, offer_id)
        if row is None:
            raise LookupError(f"Offre {offer_id} introuvable")
        offer = to_schema(row)
    with llm.track() as usage:
        state = run_agent(offer, profile)
    draft = state["best_draft"]
    report = state["best_report"]
    with SessionLocal() as db:
        d = DraftRow(
            offer_id=offer_id,
            content=draft.model_dump(),
            grounding=report.model_dump(),
            unsupported_rate=report.unsupported_rate,
            attempts=state["attempts"],
            usage=usage.snapshot(),
            model=s.llm_strong_model,
            prompt_version=s.prompt_version,
        )
        db.add(d)
        db.commit()
        return serialize_draft(d)


def serialize_draft(d: DraftRow) -> dict:
    return {
        "id": d.id,
        "offer_id": d.offer_id,
        "status": d.status,
        "content": d.content,
        "edited_content": d.edited_content,
        "grounding": d.grounding,
        "unsupported_rate": d.unsupported_rate,
        "attempts": d.attempts,
        "usage": d.usage,
        "reject_reason": d.reject_reason,
    }


def list_drafts(status: str | None = "pending") -> list[dict]:
    with SessionLocal() as db:
        q = select(DraftRow).order_by(DraftRow.created_at.desc())
        if status:
            q = q.where(DraftRow.status == status)
        return [serialize_draft(d) for d in db.scalars(q)]


def review_draft(draft_id: int, action: str, edited: dict | None, reason: str | None) -> dict:
    """Chaque décision humaine est stockée : c'est le jeu de données d'amélioration continue."""
    if action not in {"approve", "edit", "reject"}:
        raise ValueError("action ∈ {approve, edit, reject}")
    with SessionLocal() as db:
        d = db.get(DraftRow, draft_id)
        if d is None:
            raise LookupError(f"Brouillon {draft_id} introuvable")
        d.status = {"approve": "approved", "edit": "edited", "reject": "rejected"}[action]
        if action == "edit":
            d.edited_content = edited
        if action == "reject":
            d.reject_reason = reason
        d.reviewed_at = datetime.now(UTC)
        db.commit()
        return serialize_draft(d)

import hashlib
import re
import unicodedata

from ..schemas import JobOffer


def _norm(text: str | None) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text.lower()).split())


def fingerprint(offer: JobOffer) -> str:
    key = "|".join(_norm(x) for x in (offer.title, offer.company, offer.location))
    return hashlib.sha1(key.encode()).hexdigest()


def _shingles(text: str, k: int = 5) -> set[tuple[str, ...]]:
    words = _norm(text).split()
    return {tuple(words[i : i + k]) for i in range(max(len(words) - k + 1, 1))}


def jaccard(a: str, b: str) -> float:
    sa, sb = _shingles(a), _shingles(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def is_near_duplicate(a: JobOffer, b: JobOffer, threshold: float = 0.8) -> bool:
    if _norm(a.company) != _norm(b.company) or _norm(a.title) != _norm(b.title):
        return False
    return jaccard(a.description, b.description) >= threshold


def dedupe(offers: list[JobOffer]) -> list[JobOffer]:
    """Dédup exacte (empreinte) puis quasi-doublons (même entreprise + titre, texte similaire)."""
    seen: set[str] = set()
    buckets: dict[tuple[str, str], list[JobOffer]] = {}
    kept: list[JobOffer] = []
    for offer in offers:
        fp = fingerprint(offer)
        if fp in seen:
            continue
        bucket = buckets.setdefault((_norm(offer.company), _norm(offer.title)), [])
        if any(is_near_duplicate(offer, other) for other in bucket):
            continue
        seen.add(fp)
        bucket.append(offer)
        kept.append(offer)
    return kept

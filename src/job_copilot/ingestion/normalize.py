import html
import re
from datetime import datetime

from ..schemas import JobOffer

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")


def clean_text(raw: str | None) -> str:
    if not raw:
        return ""
    text = _TAG.sub(" ", html.unescape(raw))
    text = _WS.sub(" ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def from_france_travail(raw: dict) -> JobOffer:
    return JobOffer(
        source="france_travail",
        source_id=str(raw["id"]),
        title=clean_text(raw.get("intitule")),
        company=(raw.get("entreprise") or {}).get("nom"),
        location=(raw.get("lieuTravail") or {}).get("libelle"),
        description=clean_text(raw.get("description")),
        url=(raw.get("origineOffre") or {}).get("urlOrigine"),
        contract_type=raw.get("typeContrat"),
        published_at=_parse_dt(raw.get("dateCreation")),
    )


def from_rss_entry(feed_name: str, entry: dict) -> JobOffer:
    return JobOffer(
        source=f"rss:{feed_name}",
        source_id=str(entry.get("id") or entry.get("link")),
        title=clean_text(entry.get("title")),
        company=None,
        description=clean_text(entry.get("summary")),
        url=entry.get("link"),
    )

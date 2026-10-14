from job_copilot.ingestion.dedup import dedupe, fingerprint, is_near_duplicate
from job_copilot.ingestion.normalize import clean_text, from_france_travail
from job_copilot.schemas import JobOffer

DESC = "Nous cherchons un ingénieur MLOps pour déployer et monitorer des modèles en production."


def offer(i: str, title="Ingénieur MLOps", company="Acme", desc=DESC, loc="Bordeaux"):
    return JobOffer(
        source="t", source_id=i, title=title, company=company, location=loc, description=desc
    )


def test_clean_text_strips_html_and_entities():
    assert clean_text("<p>Python &amp; SQL</p>\n\n\n<b>Docker</b>") == "Python & SQL\n\nDocker"


def test_france_travail_mapping():
    raw = {
        "id": "123",
        "intitule": "Data <b>Scientist</b>",
        "description": "ML &amp; SQL",
        "entreprise": {"nom": "Acme"},
        "lieuTravail": {"libelle": "33 - Bordeaux"},
        "origineOffre": {"urlOrigine": "https://x"},
        "typeContrat": "CDI",
        "dateCreation": "2026-10-01T08:00:00.000Z",
    }
    o = from_france_travail(raw)
    assert (o.source_id, o.company, o.contract_type) == ("123", "Acme", "CDI")
    assert "Scientist" in o.title and "<" not in o.title
    assert o.published_at is not None


def test_fingerprint_ignores_case_and_accents():
    assert fingerprint(offer("1", title="Ingénieur MLOps")) == fingerprint(
        offer("2", title="INGENIEUR  mlops")
    )


def test_near_duplicate_and_distinct():
    a = offer("1")
    b = offer("2", desc=DESC + " Télétravail partiel.", loc="Pessac")
    c = offer("3", title="Data Analyst", desc="Tableaux de bord Power BI et reporting mensuel.")
    assert is_near_duplicate(a, b, threshold=0.6)
    assert not is_near_duplicate(a, c)
    assert [o.source_id for o in dedupe([a, a.model_copy(update={"source_id": "9"}), c])] == [
        "1",
        "3",
    ]

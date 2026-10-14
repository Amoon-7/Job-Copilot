from datetime import datetime

from pydantic import BaseModel, Field


# ---------- Offres ----------
class JobOffer(BaseModel):
    source: str = "manual"
    source_id: str
    title: str
    company: str | None = None
    location: str | None = None
    description: str = ""
    url: str | None = None
    contract_type: str | None = None
    published_at: datetime | None = None

    def as_text(self) -> str:
        parts = [self.title, self.company or "", self.location or "", self.description]
        return "\n".join(p for p in parts if p)


# ---------- Profil candidat ----------
class Experience(BaseModel):
    title: str
    company: str
    period: str = ""
    bullets: list[str] = []


class Project(BaseModel):
    name: str
    description: str
    tags: list[str] = []


class Education(BaseModel):
    school: str
    degree: str
    period: str = ""


class CandidateProfile(BaseModel):
    name: str
    headline: str = ""
    summary: str = ""
    skills: list[str] = []
    experiences: list[Experience] = []
    projects: list[Project] = []
    education: list[Education] = []
    languages: list[str] = []

    def evidence(self) -> dict[str, str]:
        """Passages numérotés du CV : base de l'ancrage (grounding) du vérificateur."""
        items: list[str] = []
        if self.headline:
            items.append(self.headline)
        if self.summary:
            items.append(self.summary)
        if self.skills:
            items.append("Compétences : " + ", ".join(self.skills))
        for e in self.experiences:
            for b in e.bullets:
                items.append(f"{e.title} @ {e.company} ({e.period}) : {b}")
        for p in self.projects:
            tags = f" [{', '.join(p.tags)}]" if p.tags else ""
            items.append(f"Projet {p.name}{tags} : {p.description}")
        for ed in self.education:
            items.append(f"Formation : {ed.degree}, {ed.school} ({ed.period})")
        if self.languages:
            items.append("Langues : " + ", ".join(self.languages))
        return {f"E{i}": t for i, t in enumerate(items, 1)}

    def as_text(self) -> str:
        return "\n".join(f"[{k}] {v}" for k, v in self.evidence().items())


# ---------- Sorties structurées des LLM ----------
class RerankOutput(BaseModel):
    score: int = Field(ge=0, le=100)
    rationale: str
    strengths: list[str] = []
    gaps: list[str] = []


class OfferAnalysis(BaseModel):
    requirements: list[str] = []
    keywords: list[str] = []
    tone: str = "professionnel"
    language: str = "fr"


class DraftContent(BaseModel):
    cover_letter: str
    cv_highlights: list[str] = []

    def as_text(self) -> str:
        return self.cover_letter + "\n" + "\n".join(self.cv_highlights)


class Claim(BaseModel):
    text: str
    evidence_ids: list[str] = []
    supported: bool = False
    source: str = "llm"  # "llm" ou "guard" (garde-fou déterministe)


class ClaimExtraction(BaseModel):
    claims: list[Claim] = []


class GroundingReport(BaseModel):
    claims: list[Claim] = []

    @property
    def unsupported(self) -> list[Claim]:
        return [c for c in self.claims if not c.supported]

    @property
    def unsupported_rate(self) -> float:
        return len(self.unsupported) / len(self.claims) if self.claims else 0.0

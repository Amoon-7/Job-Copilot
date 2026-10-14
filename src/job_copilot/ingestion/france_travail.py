"""API « Offres d'emploi v2 » de France Travail (https://francetravail.io)."""

import httpx

from .normalize import from_france_travail

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"
PAGE = 150


class FranceTravailConnector:
    name = "france_travail"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        keywords: str,
        department: str | None = None,
        max_results: int = 150,
    ):
        self.client_id, self.client_secret = client_id, client_secret
        self.keywords, self.department, self.max_results = keywords, department, max_results

    def _token(self, client: httpx.Client) -> str:
        r = client.post(
            TOKEN_URL,
            params={"realm": "/partenaire"},
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": SCOPE,
            },
        )
        r.raise_for_status()
        return r.json()["access_token"]

    def fetch(self):
        offers = []
        with httpx.Client(timeout=30) as client:
            headers = {"Authorization": f"Bearer {self._token(client)}"}
            start = 0
            while start < self.max_results:
                params = {"motsCles": self.keywords, "range": f"{start}-{start + PAGE - 1}"}
                if self.department:
                    params["departement"] = self.department
                r = client.get(SEARCH_URL, params=params, headers=headers)
                if r.status_code == 204:  # aucun résultat
                    break
                r.raise_for_status()
                results = r.json().get("resultats", [])
                offers.extend(from_france_travail(x) for x in results)
                if len(results) < PAGE:
                    break
                start += PAGE
        return offers

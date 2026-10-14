from typing import Protocol

from ..schemas import JobOffer


class Connector(Protocol):
    name: str

    def fetch(self) -> list[JobOffer]: ...

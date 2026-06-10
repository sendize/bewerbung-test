from dataclasses import dataclass, field
from datetime import date
import csv


@dataclass
class Regulation:
    gesetz: str  # law name (BImSchG, KrWG, etc.)
    paragraph: str  # §number (e.g. "§5")
    titel: str  # title
    text_hash: str  # content fingerprint
    status: str  # in_force / aufgehoben
    gueltig_ab: date  # effective date
    kommentar: str = ""  # change notes
    keys: tuple = ()

    def __post_init__(self):
        self.keys = (self.gesetz, self.paragraph)

    @staticmethod
    def from_csv(filepath: str) -> list["Regulation"]:
        with open(filepath, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            return [Regulation.from_csv_row(row) for row in list(reader)]

    @classmethod
    def from_csv_row(cls, row: dict) -> "Regulation":
        return cls(
            gesetz=row["gesetz"],
            paragraph=row["paragraph"],
            titel=row["titel"],
            text_hash=row["text_hash"],
            status=(row["status"]),
            gueltig_ab=date.fromisoformat(row["gueltig_ab"]),
            kommentar=row.get("kommentar", ""),
        )

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequestPrescription
from care.users.models import User


@dataclass
class Context:
    encounter: Encounter
    user: User
    recorded_at: datetime
    document_id: UUID
    prescription: MedicationRequestPrescription | None = None
    created: dict[str, list[str]] = field(default_factory=dict)
    notes: dict[str, list[str]] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    @property
    def audit(self) -> dict:
        return {"created_by": self.user, "updated_by": self.user}

    @property
    def scope(self) -> dict:
        return {"encounter": self.encounter, "patient": self.encounter.patient}

    def add_created(self, resource: str, obj) -> None:
        self.created.setdefault(resource, []).append(str(obj.external_id))

    def add_note(self, link_id: str, values: list[str]) -> None:
        self.notes.setdefault(link_id, []).extend(v for v in values if v)

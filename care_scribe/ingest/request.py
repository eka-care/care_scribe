from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class SectionKind(str, Enum):
    list = "LIST"
    narrative = "NARRATIVE"
    key_value = "KEY_VALUE"
    patient_medical_history = "PATIENT_MEDICAL_HISTORY"
    medication_table = "MEDICATION_TABLE"
    vital_table = "VITAL_TABLE"
    examination_findings = "EXAMINATION_FINDINGS"
    diagnosis = "DIAGNOSIS"
    lab_investigations = "LAB_INVESTIGATIONS"


class SectionStatus(BaseModel):
    state: str
    error: str | None = None


class Section(BaseModel):
    key: str
    display_name: str
    kind: SectionKind | str
    payload: dict
    order: int
    status: SectionStatus
    edited_by_user: bool = False

    @property
    def is_ready(self) -> bool:
        return self.status.state == "ready"


class Request(BaseModel):
    sections: list[Section]
    session_id: str
    document_id: UUID
    published_at: int


class ListPayload(BaseModel):
    items: list[str] = []


class NarrativePayload(BaseModel):
    markdown: str = ""


class KeyValue(BaseModel):
    key: str
    value: str


class KeyValuePayload(BaseModel):
    items: list[KeyValue] = []


class Header(BaseModel):
    key: str
    label: str
    type: str


class TablePayload(BaseModel):
    headers: list[Header] = []
    rows: list[dict[str, str]] = []

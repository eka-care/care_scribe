from datetime import datetime
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel


class FhirModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Coding(FhirModel):
    system: str | None = None
    code: str | None = None
    display: str | None = None


class CodeableConcept(FhirModel):
    coding: list[Coding] = []
    text: str | None = None

    @property
    def label(self) -> str:
        if self.text:
            return self.text
        return next(
            (c.display or c.code for c in self.coding if c.display or c.code), ""
        )

    @property
    def first_code(self) -> str | None:
        return next((c.code for c in self.coding if c.code), None)


class CodeableReference(FhirModel):
    concept: CodeableConcept


class Annotation(FhirModel):
    text: str = ""


class Quantity(FhirModel):
    value: float | None = None
    unit: str | None = None
    code: str | None = None


class Identifier(FhirModel):
    system: str | None = None
    value: str | None = None


class Entry(FhirModel):
    resource: dict


class Bundle(FhirModel):
    resource_type: Literal["Bundle"]
    id: str | None = None
    identifier: Identifier | None = None
    timestamp: datetime | None = None
    entry: list[Entry] = []

    @model_validator(mode="after")
    def require_document_key(self):
        if not self.document_key:
            msg = "bundle needs identifier.value or id"
            raise ValueError(msg)
        return self

    @property
    def document_key(self) -> str | None:
        return (self.identifier and self.identifier.value) or self.id

    @property
    def document_id(self) -> UUID:
        try:
            return UUID(self.document_key)
        except ValueError:
            return uuid5(NAMESPACE_URL, self.document_key)


class Request(BaseModel):
    bundle: Bundle
    session_id: str


class Condition(FhirModel):
    clinical_status: CodeableConcept | None = None
    verification_status: CodeableConcept | None = None
    category: list[CodeableConcept] = []
    code: CodeableConcept
    onset_string: str | None = None
    onset_date_time: str | None = None
    note: list[Annotation] = []


class AllergyIntolerance(FhirModel):
    clinical_status: CodeableConcept | None = None
    verification_status: CodeableConcept | None = None
    category: list[str] = []
    code: CodeableConcept
    onset_string: str | None = None
    onset_date_time: str | None = None
    note: list[Annotation] = []


class Dosage(FhirModel):
    text: str | None = None
    additional_instruction: list[CodeableConcept] = []
    as_needed: bool = False
    route: CodeableConcept | None = None


class MedicationStatement(FhirModel):
    status: str | None = None
    medication: CodeableReference
    reason: list[CodeableReference] = []
    dosage: list[Dosage] = []
    note: list[Annotation] = []


class MedicationRequest(FhirModel):
    status: str | None = None
    intent: str | None = None
    medication: CodeableReference
    dosage_instruction: list[Dosage] = []
    note: list[Annotation] = []


class Observation(FhirModel):
    category: list[CodeableConcept] = []
    code: CodeableConcept
    value_quantity: Quantity | None = None
    value_string: str | None = None
    value_codeable_concept: CodeableConcept | None = None
    effective_date_time: str | None = None
    interpretation: list[CodeableConcept] = []
    note: list[Annotation] = []


class ServiceRequest(FhirModel):
    intent: str | None = None
    category: list[CodeableConcept] = []
    code: CodeableReference
    note: list[Annotation] = []


class CommunicationPayload(FhirModel):
    content_codeable_concept: CodeableConcept | None = None
    content_string: str | None = None


class Communication(FhirModel):
    category: list[CodeableConcept] = []
    payload: list[CommunicationPayload] = []


class CarePlan(FhirModel):
    category: list[CodeableConcept] = []
    description: str | None = None


class FamilyMemberCondition(FhirModel):
    code: CodeableConcept


class FamilyMemberHistory(FhirModel):
    relationship: CodeableConcept | None = None
    condition: list[FamilyMemberCondition] = []
    note: list[Annotation] = []


class Immunization(FhirModel):
    vaccine_code: CodeableConcept
    occurrence_string: str | None = None
    occurrence_date_time: str | None = None
    note: list[Annotation] = []


class Procedure(FhirModel):
    code: CodeableConcept
    note: list[Annotation] = []

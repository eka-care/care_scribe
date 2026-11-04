from pydantic import ValidationError

from care_scribe.fhir import request as fhir
from care_scribe.fhir.request import CodeableConcept
from care_scribe.ingest.coding import (
    ALLERGY_VALUESET,
    CONDITION_VALUESET,
    MEDICATION_VALUESET,
    OBSERVATION_VALUESET,
    PROCEDURE_VALUESET,
    Lookup,
)

OBSERVATION_VALUESETS = {
    "symptom": CONDITION_VALUESET,
    "exam": CONDITION_VALUESET,
    "vital-signs": OBSERVATION_VALUESET,
    "laboratory": OBSERVATION_VALUESET,
}


def bundle_lookups(bundle: fhir.Bundle) -> set[Lookup]:
    """The texts the writers will code, so they can be looked up together; a miss only means a slower lookup later."""
    lookups = set()
    for entry in bundle.entry:
        try:
            lookups.update(resource_lookups(entry.resource))
        except ValidationError:
            continue
    return lookups


def resource_lookups(resource: dict) -> list[Lookup]:
    match resource.get("resourceType"):
        case "Condition":
            concepts = [
                (CONDITION_VALUESET, fhir.Condition.model_validate(resource).code)
            ]
        case "AllergyIntolerance":
            allergy = fhir.AllergyIntolerance.model_validate(resource)
            concepts = [(ALLERGY_VALUESET, allergy.code)]
        case "MedicationStatement":
            statement = fhir.MedicationStatement.model_validate(resource)
            concepts = [(MEDICATION_VALUESET, statement.medication.concept)]
        case "MedicationRequest":
            request = fhir.MedicationRequest.model_validate(resource)
            concepts = [(MEDICATION_VALUESET, request.medication.concept)]
        case "Observation":
            observation = fhir.Observation.model_validate(resource)
            category = next(
                (c.first_code for c in observation.category if c.first_code), None
            )
            slug = OBSERVATION_VALUESETS.get(category)
            concepts = [(slug, observation.code)] if slug else []
        case "ServiceRequest":
            order = fhir.ServiceRequest.model_validate(resource)
            concepts = [(PROCEDURE_VALUESET, order.code.concept)]
        case _:
            concepts = []
    return [(slug, c.label) for slug, c in concepts if needs_lookup(c)]


def needs_lookup(concept: CodeableConcept) -> bool:
    return bool(concept.label) and not any(c.code for c in concept.coding)

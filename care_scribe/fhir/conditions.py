from care_scribe.fhir.coding import care_status, coded, note_text
from care_scribe.fhir.notes import add_heading_note
from care_scribe.fhir.request import AllergyIntolerance, Condition
from care_scribe.ingest.coding import ALLERGY_VALUESET, CONDITION_VALUESET
from care_scribe.ingest.conditions import create_condition
from care_scribe.ingest.context import Context
from care_scribe.ingest.medical_history import create_allergy
from care_scribe.ingest.text import joined

CONDITION_CATEGORIES = {
    "encounter-diagnosis": "encounter_diagnosis",
    "problem-list-item": "chronic_condition",
}
CONDITION_CLINICAL = {
    "active",
    "recurrence",
    "relapse",
    "inactive",
    "remission",
    "resolved",
    "unknown",
}
CONDITION_VERIFICATION = {
    "unconfirmed",
    "provisional",
    "differential",
    "confirmed",
    "refuted",
    "entered_in_error",
}
ALLERGY_CATEGORIES = {"food", "medication", "environment", "biologic"}
ALLERGY_CLINICAL = {"active", "inactive", "resolved"}
ALLERGY_VERIFICATION = {
    "unconfirmed",
    "presumed",
    "confirmed",
    "refuted",
    "entered_in_error",
}


def write_condition(ctx: Context, resource: dict) -> None:
    condition = Condition.model_validate(resource)
    category = next(
        (
            CONDITION_CATEGORIES[c.code]
            for cat in condition.category
            for c in cat.coding
            if c.code in CONDITION_CATEGORIES
        ),
        None,
    )
    if category is None:
        add_heading_note(
            ctx, "Condition", [joined(condition.code.label, note_text(condition.note))]
        )
        return
    default_verification = (
        "unconfirmed" if category == "encounter_diagnosis" else "confirmed"
    )
    create_condition(
        ctx,
        code=coded(condition.code, CONDITION_VALUESET),
        category=category,
        verification=care_status(
            condition.verification_status,
            CONDITION_VERIFICATION,
            default_verification,
        ),
        clinical_status=care_status(
            condition.clinical_status, CONDITION_CLINICAL, "active"
        ),
        since=condition.onset_string or condition.onset_date_time,
        note=note_text(condition.note),
    )


def write_allergy(ctx: Context, resource: dict) -> None:
    allergy = AllergyIntolerance.model_validate(resource)
    create_allergy(
        ctx,
        code=coded(allergy.code, ALLERGY_VALUESET),
        category=next((c for c in allergy.category if c in ALLERGY_CATEGORIES), None),
        clinical_status=care_status(
            allergy.clinical_status, ALLERGY_CLINICAL, "active"
        ),
        verification=care_status(
            allergy.verification_status, ALLERGY_VERIFICATION, "unconfirmed"
        ),
        since=allergy.onset_string or allergy.onset_date_time,
        note=note_text(allergy.note),
    )

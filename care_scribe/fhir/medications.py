from care_scribe.fhir.coding import care_status, coded, note_text
from care_scribe.fhir.request import Dosage, MedicationRequest, MedicationStatement
from care_scribe.ingest.coding import MEDICATION_VALUESET
from care_scribe.ingest.context import Context
from care_scribe.ingest.medications import create_request, create_statement
from care_scribe.ingest.text import joined

STATEMENT_STATUSES = {
    "active",
    "on_hold",
    "completed",
    "stopped",
    "unknown",
    "entered_in_error",
    "not_taken",
    "intended",
}
REQUEST_STATUSES = {
    "active",
    "on_hold",
    "ended",
    "stopped",
    "completed",
    "cancelled",
    "entered_in_error",
    "draft",
    "unknown",
}
REQUEST_INTENTS = {
    "proposal",
    "plan",
    "order",
    "original_order",
    "reflex_order",
    "filler_order",
    "instance_order",
}


def write_statement(ctx: Context, resource: dict) -> None:
    statement = MedicationStatement.model_validate(resource)
    reasons = ", ".join(r.concept.label for r in statement.reason)
    create_statement(
        ctx,
        medication=coded(statement.medication.concept, MEDICATION_VALUESET),
        dosage_text=joined(*(d.text for d in statement.dosage)),
        note=joined(
            f"Reason: {reasons}" if reasons else None, note_text(statement.note)
        )
        or None,
        status=care_status(statement.status, STATEMENT_STATUSES, "active"),
    )


def write_request(ctx: Context, resource: dict) -> None:
    request = MedicationRequest.model_validate(resource)
    dosage = request.dosage_instruction[0] if request.dosage_instruction else Dosage()
    create_request(
        ctx,
        medication=coded(request.medication.concept, MEDICATION_VALUESET),
        dosage_instruction=dosage_instruction(dosage),
        status=care_status(request.status, REQUEST_STATUSES, "active"),
        intent=care_status(request.intent, REQUEST_INTENTS, "order"),
        note=note_text(request.note),
    )


def dosage_instruction(dosage: Dosage) -> dict:
    instruction = {
        "text": dosage.text,
        "patient_instruction": joined(*(i.label for i in dosage.additional_instruction))
        or None,
        "as_needed_boolean": dosage.as_needed,
    }
    if dosage.route and (
        route := next((c for c in dosage.route.coding if c.code), None)
    ):
        instruction["route"] = route.model_dump(exclude_none=True)
    return instruction

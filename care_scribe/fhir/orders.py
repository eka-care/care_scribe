from care_scribe.fhir.coding import care_status, coded, note_text
from care_scribe.fhir.notes import add_heading_note
from care_scribe.fhir.request import ServiceRequest
from care_scribe.ingest.coding import PROCEDURE_VALUESET
from care_scribe.ingest.context import Context
from care_scribe.ingest.service_requests import create_service_request
from care_scribe.ingest.text import joined

SNOMED_CATEGORIES = {
    "108252007": "laboratory",
    "363679005": "imaging",
    "387713003": "surgical_procedure",
    "409063005": "counselling",
    "409073007": "education",
}
INTENTS = {"proposal", "plan", "directive", "order"}


def write_service_request(ctx: Context, resource: dict) -> None:
    order = ServiceRequest.model_validate(resource)
    title = order.code.concept.label
    category = next(
        (
            SNOMED_CATEGORIES[c.code]
            for cat in order.category
            for c in cat.coding
            if c.code in SNOMED_CATEGORIES
        ),
        None,
    )
    if category is None:
        add_heading_note(ctx, "Orders", [joined(title, note_text(order.note))])
        return
    create_service_request(
        ctx,
        title=title,
        code=coded(order.code.concept, PROCEDURE_VALUESET),
        category=category,
        note=note_text(order.note),
        intent=care_status(order.intent, INTENTS, "order"),
    )

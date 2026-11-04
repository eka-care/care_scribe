from care_scribe.fhir.coding import note_text
from care_scribe.fhir.request import (
    CarePlan,
    Communication,
    FamilyMemberHistory,
    Immunization,
    Procedure,
)
from care_scribe.ingest.context import Context
from care_scribe.ingest.questions import (
    ADVICES,
    FOLLOW_UP_INSTRUCTIONS,
    HISTORY_OF_PRESENT_ILLNESS,
    OTHER,
)
from care_scribe.ingest.text import joined

HEADING_QUESTIONS = {
    "history of present illness": HISTORY_OF_PRESENT_ILLNESS,
    "advice": ADVICES,
    "advices": ADVICES,
    "follow-up": FOLLOW_UP_INSTRUCTIONS,
    "follow up": FOLLOW_UP_INSTRUCTIONS,
}


def add_heading_note(ctx: Context, heading: str, values: list[str]) -> None:
    if link_id := HEADING_QUESTIONS.get(heading.lower()):
        ctx.add_note(link_id, values)
        return
    ctx.add_note(OTHER, [f"{heading}: {v}" for v in values if v])


def write_communication(ctx: Context, resource: dict) -> None:
    communication = Communication.model_validate(resource)
    values = [
        (p.content_codeable_concept and p.content_codeable_concept.label)
        or p.content_string
        or ""
        for p in communication.payload
    ]
    add_heading_note(ctx, heading_of(communication.category, "Notes"), values)


def write_care_plan(ctx: Context, resource: dict) -> None:
    plan = CarePlan.model_validate(resource)
    add_heading_note(ctx, heading_of(plan.category, "Plan"), [plan.description or ""])


def write_family_history(ctx: Context, resource: dict) -> None:
    history = FamilyMemberHistory.model_validate(resource)
    relation = history.relationship.label if history.relationship else "relative"
    conditions = "; ".join(c.code.label for c in history.condition)
    add_heading_note(
        ctx,
        "Family history",
        [joined(f"{relation}: {conditions}", note_text(history.note))],
    )


def write_immunization(ctx: Context, resource: dict) -> None:
    immunization = Immunization.model_validate(resource)
    when = immunization.occurrence_date_time or immunization.occurrence_string
    add_heading_note(
        ctx,
        "Vaccination history",
        [
            joined(
                immunization.vaccine_code.label,
                f"when: {when}" if when else None,
                note_text(immunization.note),
            )
        ],
    )


def write_procedure(ctx: Context, resource: dict) -> None:
    procedure = Procedure.model_validate(resource)
    add_heading_note(
        ctx,
        "Procedures performed",
        [joined(procedure.code.label, note_text(procedure.note))],
    )


def heading_of(category, default: str) -> str:
    return next((c.label for c in category if c.label), default)

from datetime import datetime

from django.utils.timezone import is_aware, make_aware

from care_scribe.fhir.coding import coded, note_text
from care_scribe.fhir.notes import add_heading_note
from care_scribe.fhir.request import Observation
from care_scribe.ingest.coding import CONDITION_VALUESET, OBSERVATION_VALUESET
from care_scribe.ingest.conditions import create_condition
from care_scribe.ingest.context import Context
from care_scribe.ingest.observations import (
    EXAM,
    LABORATORY,
    VITAL_SIGNS,
    create_observation,
)
from care_scribe.ingest.questions import MEDICAL_HISTORY
from care_scribe.ingest.text import joined


def write_observation(ctx: Context, resource: dict) -> None:
    observation = Observation.model_validate(resource)
    category = next(
        (cat.first_code for cat in observation.category if cat.first_code), None
    )
    match category:
        case "symptom":
            create_condition(
                ctx,
                code=coded(observation.code, CONDITION_VALUESET),
                category="problem_list_item",
                verification="confirmed",
                note=note_text(observation.note),
            )
        case "vital-signs":
            write_measurement(ctx, observation, VITAL_SIGNS, OBSERVATION_VALUESET)
        case "exam":
            write_measurement(ctx, observation, EXAM, CONDITION_VALUESET)
        case "laboratory":
            write_measurement(ctx, observation, LABORATORY, OBSERVATION_VALUESET)
        case "social-history":
            ctx.add_note(MEDICAL_HISTORY, [observation_text(observation)])
        case _:
            add_heading_note(ctx, "Observation", [observation_text(observation)])


def write_measurement(
    ctx: Context, observation: Observation, category: dict, valueset_slug: str
) -> None:
    value_type, value = value_of(observation)
    effective = parse_datetime(observation.effective_date_time)
    unparsed_date = observation.effective_date_time if effective is None else None
    create_observation(
        ctx,
        category=category,
        code=coded(observation.code, valueset_slug),
        value_type=value_type,
        value=value,
        note=joined(
            f"Date: {unparsed_date}" if unparsed_date else None,
            *(i.label for i in observation.interpretation),
            note_text(observation.note),
        ),
        effective_datetime=effective,
    )


def value_of(observation: Observation) -> tuple[str, dict]:
    quantity = observation.value_quantity
    if quantity and quantity.value is not None:
        value = {"value": f"{quantity.value:g}"}
        if unit := quantity.unit or quantity.code:
            value["unit"] = {"code": quantity.code or unit, "display": unit}
        return "decimal", value
    if observation.value_codeable_concept:
        return "string", {"value": observation.value_codeable_concept.label}
    return "string", {"value": observation.value_string or ""}


def observation_text(observation: Observation) -> str:
    _, value = value_of(observation)
    return joined(observation.code.label, value["value"], note_text(observation.note))


def parse_datetime(value: str | None) -> datetime | None:
    """A full ISO date or datetime; partial dates such as 2026-07 return None."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if is_aware(parsed) else make_aware(parsed)

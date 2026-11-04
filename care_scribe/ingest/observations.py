from care.emr.models.observation import Observation

from care_scribe.ingest.coding import (
    CONDITION_VALUESET,
    OBSERVATION_VALUESET,
    code_from_text,
)
from care_scribe.ingest.context import Context
from care_scribe.ingest.request import Section, TablePayload
from care_scribe.ingest.text import joined

CATEGORY_SYSTEM = "http://terminology.hl7.org/CodeSystem/observation-category"
VITAL_SIGNS = {
    "system": CATEGORY_SYSTEM,
    "code": "vital-signs",
    "display": "Vital Signs",
}
EXAM = {"system": CATEGORY_SYSTEM, "code": "exam", "display": "Exam"}


def create_vitals(ctx: Context, section: Section) -> None:
    for row in TablePayload.model_validate(section.payload).rows:
        value = {"value": row["value"]}
        if unit := row.get("unit"):
            value["unit"] = {"code": unit, "display": unit}
        normal_range = row.get("normal_range")
        create_observation(
            ctx,
            category=VITAL_SIGNS,
            code=code_from_text(OBSERVATION_VALUESET, row["vital_name"]),
            value_type="decimal" if is_number(row["value"]) else "string",
            value=value,
            note=joined(
                f"Normal range: {normal_range}" if normal_range else None,
                row.get("notes"),
            ),
        )


def create_exam_findings(ctx: Context, section: Section) -> None:
    for row in TablePayload.model_validate(section.payload).rows:
        create_observation(
            ctx,
            category=EXAM,
            code=code_from_text(CONDITION_VALUESET, row["finding"]),
            value_type="string",
            value={"value": row.get("status", "")},
            note=row.get("detail", ""),
        )


def create_observation(
    ctx: Context, *, category: dict, code: dict, value_type: str, value: dict, note: str
) -> None:
    observation = Observation.objects.create(
        **ctx.scope,
        **ctx.audit,
        status="final",
        category=category,
        main_code=code,
        subject_type="encounter",
        subject_id=ctx.encounter.external_id,
        effective_datetime=ctx.recorded_at,
        data_entered_by=ctx.user,
        value_type=value_type,
        value=value,
        note=note,
    )
    ctx.add_created("observation", observation)


def is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True

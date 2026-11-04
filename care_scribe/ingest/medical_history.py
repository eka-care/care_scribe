from care.emr.models.allergy_intolerance import AllergyIntolerance

from care_scribe.ingest.coding import (
    ALLERGY_VALUESET,
    CONDITION_VALUESET,
    code_from_text,
)
from care_scribe.ingest.conditions import create_condition
from care_scribe.ingest.context import Context
from care_scribe.ingest.questions import MEDICAL_HISTORY
from care_scribe.ingest.request import Section, TablePayload
from care_scribe.ingest.text import row_text

ALLERGY_CATEGORIES = {
    "food_allergy": "food",
    "drug_allergy": "medication",
    "medication_allergy": "medication",
}


def create(ctx: Context, section: Section) -> None:
    table = TablePayload.model_validate(section.payload)
    for row in table.rows:
        category = row.get("category", "")
        present = row.get("status", "").lower() == "yes"
        if present and category == "condition":
            create_condition(
                ctx,
                code=code_from_text(CONDITION_VALUESET, row["condition"]),
                category="chronic_condition",
                verification="confirmed",
                since=row.get("since"),
                note=row.get("note"),
            )
        elif present and category.endswith("allergy"):
            create_allergy(
                ctx,
                code=code_from_text(ALLERGY_VALUESET, row["condition"]),
                category=ALLERGY_CATEGORIES.get(category),
                since=row.get("since"),
                note=row.get("note"),
            )
        else:
            ctx.add_note(MEDICAL_HISTORY, [row_text(table, row)])


def create_allergy(
    ctx: Context,
    *,
    code: dict,
    category: str | None,
    clinical_status: str = "active",
    verification: str = "unconfirmed",
    since: str | None = None,
    note: str | None = None,
) -> None:
    allergy = AllergyIntolerance.objects.create(
        **ctx.scope,
        **ctx.audit,
        code=code,
        category=category,
        clinical_status=clinical_status,
        verification_status=verification,
        onset={"onset_string": since} if since else {},
        recorded_date=ctx.recorded_at,
        note=note,
    )
    ctx.add_created("allergy_intolerance", allergy)

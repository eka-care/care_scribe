from care.emr.models.condition import Condition

from care_scribe.ingest.coding import CONDITION_VALUESET, code_from_text
from care_scribe.ingest.context import Context
from care_scribe.ingest.request import ListPayload, Section, TablePayload

VERIFICATION_STATUSES = {"unconfirmed", "provisional", "differential", "confirmed"}


def create_symptoms(ctx: Context, section: Section) -> None:
    for item in ListPayload.model_validate(section.payload).items:
        create_condition(
            ctx,
            code=code_from_text(CONDITION_VALUESET, item),
            category="problem_list_item",
            verification="confirmed",
        )


def create_diagnoses(ctx: Context, section: Section) -> None:
    for row in TablePayload.model_validate(section.payload).rows:
        status = row.get("status", "").lower()
        create_condition(
            ctx,
            code=code_from_text(CONDITION_VALUESET, row["diagnosis"]),
            category="encounter_diagnosis",
            verification=status if status in VERIFICATION_STATUSES else "unconfirmed",
            since=row.get("since"),
            note=row.get("note"),
        )


def create_condition(
    ctx: Context,
    *,
    code: dict,
    category: str,
    verification: str,
    clinical_status: str = "active",
    since: str | None = None,
    note: str | None = None,
) -> None:
    condition = Condition.objects.create(
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
    ctx.add_created("condition", condition)

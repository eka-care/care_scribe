from care.emr.models.medication_request import MedicationRequest
from care.emr.models.medication_statement import MedicationStatement

from care_scribe.ingest.coding import MEDICATION_VALUESET, code_from_text
from care_scribe.ingest.context import Context
from care_scribe.ingest.request import Section, TablePayload
from care_scribe.ingest.text import joined


def create_statements(ctx: Context, section: Section) -> None:
    for row in TablePayload.model_validate(section.payload).rows:
        create_statement(
            ctx,
            medication=code_from_text(MEDICATION_VALUESET, row["drug_name"]),
            dosage_text=dosage_text(row),
            note=row.get("notes"),
        )


def create_requests(ctx: Context, section: Section) -> None:
    for row in TablePayload.model_validate(section.payload).rows:
        create_request(
            ctx,
            medication=code_from_text(MEDICATION_VALUESET, row["drug_name"]),
            dosage_instruction={
                "text": dosage_text(row),
                "patient_instruction": row.get("notes"),
                "as_needed_boolean": False,
            },
        )


def create_statement(
    ctx: Context,
    *,
    medication: dict,
    dosage_text: str,
    note: str | None,
    status: str = "active",
) -> None:
    statement = MedicationStatement.objects.create(
        **ctx.scope,
        **ctx.audit,
        medication=medication,
        status=status,
        information_source="patient",
        dosage_text=dosage_text,
        note=note,
    )
    ctx.add_created("medication_statement", statement)


def create_request(
    ctx: Context,
    *,
    medication: dict,
    dosage_instruction: dict,
    status: str = "active",
    intent: str = "order",
    note: str | None = None,
) -> None:
    category = "inpatient" if ctx.encounter.encounter_class == "imp" else "outpatient"
    request = MedicationRequest.objects.create(
        **ctx.scope,
        **ctx.audit,
        medication=medication,
        status=status,
        intent=intent,
        category=category,
        priority="routine",
        do_not_perform=False,
        dosage_instruction=[dosage_instruction],
        note=note,
        authored_on=ctx.recorded_at,
        requester=ctx.user,
    )
    ctx.add_created("medication_request", request)


def dosage_text(row: dict[str, str]) -> str:
    return joined(row.get("dosage"), row.get("frequency"), row.get("duration"))

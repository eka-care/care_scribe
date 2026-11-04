from care.emr.models.medication_request import MedicationRequest
from care.emr.models.medication_statement import MedicationStatement

from care_scribe.ingest.coding import MEDICATION_VALUESET, code_from_text
from care_scribe.ingest.context import Context
from care_scribe.ingest.request import Section, TablePayload
from care_scribe.ingest.text import joined


def create_statements(ctx: Context, section: Section) -> None:
    for row in TablePayload.model_validate(section.payload).rows:
        statement = MedicationStatement.objects.create(
            **ctx.scope,
            **ctx.audit,
            medication=code_from_text(MEDICATION_VALUESET, row["drug_name"]),
            status="active",
            information_source="patient",
            dosage_text=dosage_text(row),
            note=row.get("notes"),
        )
        ctx.add_created("medication_statement", statement)


def create_requests(ctx: Context, section: Section) -> None:
    category = "inpatient" if ctx.encounter.encounter_class == "imp" else "outpatient"
    for row in TablePayload.model_validate(section.payload).rows:
        request = MedicationRequest.objects.create(
            **ctx.scope,
            **ctx.audit,
            medication=code_from_text(MEDICATION_VALUESET, row["drug_name"]),
            status="active",
            intent="order",
            category=category,
            priority="routine",
            do_not_perform=False,
            dosage_instruction=[
                {
                    "text": dosage_text(row),
                    "patient_instruction": row.get("notes"),
                    "as_needed_boolean": False,
                }
            ],
            authored_on=ctx.recorded_at,
            requester=ctx.user,
        )
        ctx.add_created("medication_request", request)


def dosage_text(row: dict[str, str]) -> str:
    return joined(row.get("dosage"), row.get("frequency"), row.get("duration"))

from datetime import UTC, datetime

from care.emr.models.encounter import Encounter
from care.users.models import User

from care_scribe.ingest import (
    conditions,
    medical_history,
    medications,
    notes,
    observations,
    questionnaire_response,
    service_requests,
)
from care_scribe.ingest.context import Context
from care_scribe.ingest.filing import find_filed_result, record_filing
from care_scribe.ingest.request import Request, Section, SectionKind

CHIEF_COMPLAINT = "chief_complaint"
CURRENT_MEDICATIONS = "current_medications_treatment"


def ingest_scribe_document(
    encounter: Encounter, user: User, req: Request
) -> tuple[dict, bool]:
    """Writes the note's sections as clinical records once per document; returns (result, created)."""
    if (filed := find_filed_result(req.document_id, encounter)) is not None:
        return filed, False

    published_at = datetime.fromtimestamp(req.published_at, tz=UTC)
    ctx = Context(
        encounter=encounter,
        user=user,
        recorded_at=published_at,
        document_id=req.document_id,
    )
    for section in sorted(req.sections, key=lambda s: s.order):
        if not section.is_ready:
            ctx.skipped.append(section.key)
            continue
        write_section(ctx, section)
    questionnaire_response.create(ctx)

    result = {
        "document_id": str(req.document_id),
        "created": ctx.created,
        "skipped_sections": ctx.skipped,
    }
    record_filing(
        ctx,
        document_id=req.document_id,
        session_id=req.session_id,
        published_at=published_at,
        payload=req.model_dump(mode="json"),
        result=result,
    )
    return result, True


def write_section(ctx: Context, section: Section) -> None:
    match section.kind:
        case SectionKind.list if section.key == CHIEF_COMPLAINT:
            conditions.create_symptoms(ctx, section)
        case SectionKind.diagnosis:
            conditions.create_diagnoses(ctx, section)
        case SectionKind.patient_medical_history:
            medical_history.create(ctx, section)
        case SectionKind.medication_table if section.key == CURRENT_MEDICATIONS:
            medications.create_statements(ctx, section)
        case SectionKind.medication_table:
            medications.create_requests(ctx, section)
        case SectionKind.vital_table:
            observations.create_vitals(ctx, section)
        case SectionKind.examination_findings:
            observations.create_exam_findings(ctx, section)
        case SectionKind.lab_investigations:
            service_requests.create_investigations(ctx, section)
        case _:
            notes.add_section(ctx, section)

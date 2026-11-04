from datetime import datetime
from uuid import UUID

from care.emr.models.encounter import Encounter

from care_scribe.ingest.context import Context
from care_scribe.models import ScribeDocument


class DocumentInOtherEncounterError(Exception):
    pass


def find_filed_result(document_id: UUID, encounter: Encounter) -> dict | None:
    """The first result for a document already filed on this encounter, else None."""
    existing = ScribeDocument.objects.filter(document_id=document_id).first()
    if existing is None:
        return None
    if existing.encounter_id != encounter.id:
        raise DocumentInOtherEncounterError
    return existing.result


def record_filing(
    ctx: Context,
    *,
    document_id: UUID,
    session_id: str,
    published_at: datetime,
    payload: dict,
    result: dict,
) -> None:
    ScribeDocument.objects.create(
        document_id=document_id,
        session_id=session_id,
        encounter=ctx.encounter,
        published_at=published_at,
        payload=payload,
        result=result,
        created_by=ctx.user,
    )

from care.emr.models.encounter import Encounter
from care.users.models import User
from care.utils.time_util import care_now
from django.db import transaction
from django.utils.timezone import is_aware, make_aware
from pydantic import ValidationError

from care_scribe.fhir import conditions, medications, notes, observations, orders
from care_scribe.fhir.request import Request
from care_scribe.ingest import questionnaire_response
from care_scribe.ingest.context import Context
from care_scribe.ingest.filing import find_filed_result, record_filing

IGNORED_RESOURCES = {"Patient", "Practitioner", "Encounter"}
WRITERS = {
    "Condition": conditions.write_condition,
    "AllergyIntolerance": conditions.write_allergy,
    "MedicationStatement": medications.write_statement,
    "MedicationRequest": medications.write_request,
    "Observation": observations.write_observation,
    "ServiceRequest": orders.write_service_request,
    "Communication": notes.write_communication,
    "CarePlan": notes.write_care_plan,
    "FamilyMemberHistory": notes.write_family_history,
    "Immunization": notes.write_immunization,
    "Procedure": notes.write_procedure,
}


class InvalidEntryError(Exception):
    def __init__(self, index: int, resource_type: str, errors: list):
        super().__init__(f"entry {index} ({resource_type}) is not valid")
        self.errors = errors


def ingest_fhir_bundle(
    encounter: Encounter, user: User, req: Request
) -> tuple[dict, bool]:
    """Files a scribe FHIR bundle as clinical records, all or nothing, once per document; returns (result, created)."""
    bundle = req.bundle
    if (filed := find_filed_result(bundle.document_id, encounter)) is not None:
        return filed, False

    published_at = bundle.timestamp or care_now()
    if not is_aware(published_at):
        published_at = make_aware(published_at)
    ctx = Context(encounter=encounter, user=user, recorded_at=published_at)
    with transaction.atomic():
        for index, entry in enumerate(bundle.entry):
            resource_type = entry.resource.get("resourceType", "")
            try:
                write_resource(ctx, resource_type, entry.resource)
            except ValidationError as e:
                raise InvalidEntryError(
                    index,
                    resource_type,
                    e.errors(
                        include_url=False, include_input=False, include_context=False
                    ),
                ) from e
        questionnaire_response.create(ctx)
        result = {
            "document_id": str(bundle.document_id),
            "created": ctx.created,
            "skipped_resources": ctx.skipped,
        }
        record_filing(
            ctx,
            document_id=bundle.document_id,
            session_id=req.session_id,
            published_at=published_at,
            payload=req.model_dump(mode="json", by_alias=True),
            result=result,
        )
    return result, True


def write_resource(ctx: Context, resource_type: str, resource: dict) -> None:
    if resource_type in IGNORED_RESOURCES:
        return
    writer = WRITERS.get(resource_type)
    if writer is None:
        ctx.skipped.append(resource_type)
        return
    writer(ctx, resource)

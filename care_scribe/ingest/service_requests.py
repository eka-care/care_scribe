from care.emr.models.service_request import ServiceRequest

from care_scribe.ingest.coding import PROCEDURE_VALUESET, code_from_text
from care_scribe.ingest.context import Context
from care_scribe.ingest.request import Section, TablePayload
from care_scribe.ingest.text import row_text


def create_investigations(ctx: Context, section: Section) -> None:
    table = TablePayload.model_validate(section.payload)
    for row in table.rows:
        service_request = ServiceRequest.objects.create(
            **ctx.scope,
            **ctx.audit,
            facility=ctx.encounter.facility,
            title=row["investigation"],
            code=code_from_text(PROCEDURE_VALUESET, row["investigation"]),
            category="laboratory",
            status="active",
            intent="order",
            priority="routine",
            note=row_text(table, row, skip=("investigation",)) or None,
            requester=ctx.user,
        )
        ctx.add_created("service_request", service_request)

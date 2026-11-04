import json

from care_scribe.ingest.context import Context
from care_scribe.ingest.questions import OTHER, SECTION_QUESTIONS
from care_scribe.ingest.request import (
    KeyValuePayload,
    ListPayload,
    NarrativePayload,
    Section,
    SectionKind,
    TablePayload,
)
from care_scribe.ingest.text import row_text


def add_section(ctx: Context, section: Section) -> None:
    values = section_values(section)
    if section.key in SECTION_QUESTIONS:
        ctx.add_note(section.key, values)
        return
    ctx.add_note(OTHER, [f"{section.display_name}: {v}" for v in values])


def section_values(section: Section) -> list[str]:
    match section.kind:
        case SectionKind.list:
            return ListPayload.model_validate(section.payload).items
        case SectionKind.narrative:
            return [NarrativePayload.model_validate(section.payload).markdown]
        case SectionKind.key_value:
            items = KeyValuePayload.model_validate(section.payload).items
            return [f"{i.key}: {i.value}" for i in items]
    if "rows" in section.payload:
        table = TablePayload.model_validate(section.payload)
        return [row_text(table, row) for row in table.rows]
    return [json.dumps(section.payload)]

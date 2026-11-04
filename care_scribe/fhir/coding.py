from care_scribe.fhir.request import Annotation, CodeableConcept
from care_scribe.ingest.coding import code_from_text


def coded(concept: CodeableConcept, valueset_slug: str) -> dict:
    """The scribe's own coding when it sent one, else the valueset match for the text."""
    for coding in concept.coding:
        if coding.code:
            return coding.model_dump(exclude_none=True) | {
                "display": coding.display or concept.label
            }
    return code_from_text(valueset_slug, concept.label)


def care_status(
    concept: CodeableConcept | str | None, allowed: set[str], default: str
) -> str:
    """A FHIR status code in CARE's spelling (underscores), or the default when CARE lacks it."""
    code = (
        concept if isinstance(concept, str) or concept is None else concept.first_code
    )
    if code is None:
        return default
    code = code.replace("-", "_")
    return code if code in allowed else default


def note_text(notes: list[Annotation]) -> str | None:
    return "; ".join(n.text for n in notes if n.text) or None

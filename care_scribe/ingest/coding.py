import logging

import requests
from care.emr.models.valueset import ValueSet

logger = logging.getLogger(__name__)

CONDITION_VALUESET = "system-condition-code"
ALLERGY_VALUESET = "system-allergy-code"
MEDICATION_VALUESET = "system-medication"
OBSERVATION_VALUESET = "system-observation"
PROCEDURE_VALUESET = "activity-definition-procedure-code"


def code_from_text(valueset_slug: str, text: str) -> dict:
    """The top terminology match for the text, or a text-only coding when none is found."""
    matches = _search(valueset_slug, text)
    if not matches:
        return {"code": text, "display": text}
    top = matches[0]
    return {"system": top.system, "code": top.code, "display": top.display}


def _search(valueset_slug: str, text: str) -> list:
    valueset = ValueSet.objects.filter(slug=valueset_slug).first()
    if valueset is None:
        logger.warning(
            "valueset missing, coding as text", extra={"slug": valueset_slug}
        )
        return []
    try:
        return valueset.search(search=text, count=1)
    except requests.RequestException:
        logger.warning(
            "terminology search failed, coding as text",
            extra={"slug": valueset_slug},
            exc_info=True,
        )
        return []

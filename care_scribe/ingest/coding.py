import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar

import requests
from care.emr.models.valueset import ValueSet

logger = logging.getLogger(__name__)

CONDITION_VALUESET = "system-condition-code"
ALLERGY_VALUESET = "system-allergy-code"
MEDICATION_VALUESET = "system-medication"
OBSERVATION_VALUESET = "system-observation"
PROCEDURE_VALUESET = "activity-definition-procedure-code"

LOOKUP_WORKERS = 8

Lookup = tuple[str, str]

_prefetched: ContextVar[dict[Lookup, dict] | None] = ContextVar(
    "care_scribe_prefetched_codes", default=None
)


def code_from_text(valueset_slug: str, text: str) -> dict:
    """The top terminology match for the text, or a text-only coding when none is found."""
    prefetched = _prefetched.get()
    if prefetched is not None and (valueset_slug, text) in prefetched:
        return prefetched[(valueset_slug, text)]
    valueset = _valueset(valueset_slug)
    return _coding(text, _search(valueset, valueset_slug, text))


@contextmanager
def prefetched_codes(lookups: set[Lookup]) -> Iterator[None]:
    """Looks the texts up concurrently, so code_from_text calls inside the block skip the terminology server."""
    valuesets = {slug: _valueset(slug) for slug, _ in lookups}
    ordered = list(lookups)
    with ThreadPoolExecutor(max_workers=LOOKUP_WORKERS) as pool:
        matches = pool.map(
            lambda lookup: _search(valuesets[lookup[0]], *lookup), ordered
        )
        codes = {
            lookup: _coding(lookup[1], found)
            for lookup, found in zip(ordered, matches, strict=True)
        }
    token = _prefetched.set(codes)
    try:
        yield
    finally:
        _prefetched.reset(token)


def _coding(text: str, matches: list) -> dict:
    if not matches:
        return {"code": text, "display": text}
    top = matches[0]
    return {"system": top.system, "code": top.code, "display": top.display}


def _valueset(valueset_slug: str) -> ValueSet | None:
    valueset = ValueSet.objects.filter(slug=valueset_slug).first()
    if valueset is None:
        logger.warning(
            "valueset missing, coding as text", extra={"slug": valueset_slug}
        )
    return valueset


def _search(valueset: ValueSet | None, valueset_slug: str, text: str) -> list:
    if valueset is None:
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

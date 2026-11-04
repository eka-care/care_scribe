from care_scribe.ingest.request import TablePayload


def row_text(
    table: TablePayload, row: dict[str, str], skip: tuple[str, ...] = ()
) -> str:
    return ", ".join(
        f"{h.label}: {row[h.key]}"
        for h in table.headers
        if h.key not in skip and row.get(h.key)
    )


def joined(*parts: str | None) -> str:
    return ", ".join(p for p in parts if p)

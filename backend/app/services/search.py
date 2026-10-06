import re
from typing import Any

from sqlalchemy import text

from app.api.dependencies import Scope
from app.schemas.search import SearchHit


def terms(query: str) -> list[str]:
    return re.findall(r"[^\W_]+", query, re.UNICODE)[:20]


def fts_query(query: str, conjunction: str = "AND") -> str:
    return f" {conjunction} ".join('"' + term + '"*' for term in terms(query))


def find(
    scope: Scope,
    query: str,
    offset: int = 0,
    limit: int = 25,
    meeting_id: str | None = None,
    tag: str | None = None,
    participant: str | None = None,
    kind: str | None = None,
    conjunction: str = "AND",
) -> list[SearchHit]:
    expression = fts_query(query, conjunction)
    if not expression:
        return []
    conditions = ["d.workspace_id=:workspace"]
    params: dict[str, Any] = {
        "workspace": scope.workspace_id,
        "query": expression,
        "limit": limit,
        "offset": offset,
    }
    for key, value, column in [("meeting", meeting_id, "d.meeting_id"), ("kind", kind, "d.kind")]:
        if value:
            conditions.append(f"{column}=:{key}")
            params[key] = value
    if tag:
        conditions.append(
            "EXISTS(SELECT 1 FROM meeting_tags t WHERE t.meeting_id=d.meeting_"
            "id AND t.workspace_id=:workspace AND t.tag_id=:tag)"
        )
        params["tag"] = tag
    if participant:
        conditions.append(
            "EXISTS(SELECT 1 FROM meeting_participants p WHERE p.meeting_id=d."
            "meeting_id AND p.workspace_id=:workspace AND p.participant_id=:pa"
            "rticipant)"
        )
        params["participant"] = participant
    sql = (
        """SELECT d.public_id AS id,d.meeting_id,d.segment_id,d.kind,d.text,m.title,m.occurred_at,
    s.start_ms AS timestamp_ms, sp.display_name AS speaker_name
    FROM search_documents_fts JOIN search_documents d ON d.id=search_documents_fts.rowid
    JOIN meetings m ON m.id=d.meeting_id LEFT JOIN transcript_segments s ON s.public_id=d.segment_id
    LEFT JOIN meeting_speakers sp ON sp.id=s.speaker_id
    WHERE search_documents_fts MATCH :query AND """
        + " AND ".join(conditions)
        + " ORDER BY bm25(search_documents_fts),d.id LIMIT :limit OFFSET :offset"
    )
    pattern = re.compile("|".join(re.escape(term) for term in terms(query)), re.I)
    result = []
    for row in scope.db.execute(text(sql), params).mappings():
        matched = pattern.search(row["text"])
        start = max(0, (matched.start() if matched else 0) - 60)
        snippet = row["text"][start : start + 320]
        result.append(
            SearchHit.model_validate(
                dict(row)
                | {
                    "snippet": snippet,
                    "ranges": [(m.start(), m.end()) for m in pattern.finditer(snippet)],
                }
            )
        )
    return result

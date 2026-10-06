import hashlib
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from sqlalchemy import delete, func, insert, select, update

from app.api.dependencies import Scoped, Version, require_version
from app.api.segments import scoped_segment
from app.api.transcript import transcript_page
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.limits import rate_limit
from app.db.session import begin_write
from app.models import chat_citations, chat_messages, idempotency_records, meetings
from app.models.common import now, uid
from app.repositories.scoped import get_resource
from app.schemas.chat import ChatHistory, ChatMessage, ChatRequest, ChatResult, Citation
from app.services.chat import answer
from app.services.intelligence import while_connected
from app.services.operations import claim, complete, fail
from app.services.search import find

router = APIRouter(prefix="/api/v1/meetings")


def message(scope: Scoped, meeting_id: UUID, message_id: str) -> ChatMessage:
    row = get_resource(scope, chat_messages, message_id, str(meeting_id))
    citations = [
        Citation.model_validate(c)
        for c in scope.db.execute(
            select(chat_citations).where(
                chat_citations.c.workspace_id == scope.workspace_id,
                chat_citations.c.meeting_id == str(meeting_id),
                chat_citations.c.message_id == message_id,
            )
        ).mappings()
    ]
    return ChatMessage.model_validate(dict(row) | {"citations": citations})


@router.get("/{meeting_id}/chat", response_model=ChatHistory)
def history(meeting_id: UUID, scope: Scoped, cursor: int = Query(0, ge=0, le=100)) -> ChatHistory:
    meeting = get_resource(scope, meetings, str(meeting_id))
    ids = list(
        scope.db.scalars(
            select(chat_messages.c.id)
            .where(
                chat_messages.c.workspace_id == scope.workspace_id,
                chat_messages.c.meeting_id == str(meeting_id),
            )
            .order_by(chat_messages.c.created_at.desc(), chat_messages.c.id.desc())
            .offset(cursor)
            .limit(21)
        )
    )
    return ChatHistory(
        items=list(reversed([message(scope, meeting_id, key) for key in ids[:20]])),
        has_more=len(ids) > 20,
        next_cursor=cursor + 20 if len(ids) > 20 else None,
        version=meeting["version"],
        transcript_revision=meeting["transcript_revision"],
    )


@router.post("/{meeting_id}/chat", response_model=ChatResult)
async def ask(
    meeting_id: UUID,
    data: ChatRequest,
    request: Request,
    scope: Scoped,
    idempotency_key: Annotated[UUID, Header()],
    if_match: Version = None,
) -> ChatResult:
    meeting = get_resource(scope, meetings, str(meeting_id))
    rate_limit(scope.session_id, "chat", 10)
    endpoint = f"chat:{meeting_id}"
    key = str(idempotency_key)
    replay = claim(
        scope, endpoint, key, hashlib.sha256(data.model_dump_json().encode()).hexdigest()
    )
    if replay:
        return ChatResult.model_validate_json(replay)
    require_version(meeting["version"], if_match)
    if data.mode == "openai" and not data.consent:
        raise DomainError(
            422,
            "consent_required",
            "Consent to send selected meeting text to OpenAI, or choose extractive mode.",
        )
    count = (
        scope.db.scalar(
            select(func.count())
            .select_from(chat_messages)
            .where(
                chat_messages.c.workspace_id == scope.workspace_id,
                chat_messages.c.meeting_id == str(meeting_id),
            )
        )
        or 0
    )
    if count >= 100:
        raise DomainError(
            429,
            "chat_quota",
            "This meeting has 50 saved exchanges. Clear history to ask another question.",
        )
    stop = set(
        (
            "a an the and or is are was were what which who when where how why do does did "
            "can could would should about of on in to for from with this that "
            "me my please tell show meeting"
        ).split()
    )
    keywords = " ".join(
        word
        for word in re.findall(r"[^\W_]+", data.question, re.UNICODE)
        if word.casefold() not in stop
    )
    hits = find(
        scope,
        keywords,
        limit=12,
        meeting_id=str(meeting_id),
        kind="transcript",
        conjunction="OR",
    )
    rows = [scoped_segment(scope, meeting_id, hit.segment_id) for hit in hits if hit.segment_id]
    if not rows and re.search(
        r"\b(summary|summarize|overview|decisions|action items)\b", data.question, re.I
    ):
        rows = transcript_page(scope, str(meeting_id), 0, 8).items
    selected = []
    used = 0
    for row in rows:
        if used + len(row.text) > 18000:
            continue
        selected.append(row)
        used += len(row.text)
    recent = [
        {"role": m.role, "content": m.content[:600]}
        for m in history(meeting_id, scope, 0).items[-4:]
    ]
    revision = meeting["transcript_revision"]
    scope.db.commit()
    try:
        generated, provider, notice = await while_connected(
            request, answer(data.question, selected, recent, str(meeting_id), revision, data.mode)
        )
        begin_write(scope.db)
        latest = get_resource(scope, meetings, str(meeting_id))
        if latest["version"] != meeting["version"] or latest["transcript_revision"] != revision:
            raise DomainError(
                409,
                "meeting_changed",
                "The meeting or conversation changed during generation. Your quest"
                "ion is retained; retry against the latest content.",
            )
        context = {"workspace_id": scope.workspace_id, "meeting_id": str(meeting_id)}
        user_id, assistant_id = uid(), uid()
        for item_id, role, content in [
            (user_id, "user", data.question),
            (assistant_id, "assistant", generated.answer),
        ]:
            scope.db.execute(
                insert(chat_messages).values(
                    **context,
                    id=item_id,
                    conversation_id=str(meeting_id),
                    role=role,
                    content=content,
                    provider=provider,
                    model=get_settings().llm_model if provider == "openai" else None,
                    source_revision=revision,
                    created_at=now(),
                )
            )
        source = {str(row.public_id): row for row in selected}
        for citation in generated.citations:
            if citation not in source:
                raise DomainError(
                    422, "invalid_citation", "The response referred to unavailable evidence."
                )
            scope.db.execute(
                insert(chat_citations).values(
                    **context,
                    message_id=assistant_id,
                    segment_id=citation,
                    original_segment_public_id=citation,
                    source_revision=revision,
                    timestamp_ms=source[citation].start_ms,
                )
            )
        scope.db.execute(
            update(meetings)
            .where(meetings.c.id == str(meeting_id))
            .values(version=meetings.c.version + 1)
        )
        result = ChatResult(
            user=message(scope, meeting_id, user_id),
            assistant=message(scope, meeting_id, assistant_id),
            notice=notice,
        )
        complete(scope, endpoint, key, result.model_dump_json())
        return result
    except BaseException:
        fail(scope, endpoint, key)
        raise


@router.delete("/{meeting_id}/chat", status_code=204)
def clear(meeting_id: UUID, scope: Scoped, if_match: Version = None) -> None:
    meeting = get_resource(scope, meetings, str(meeting_id))
    require_version(meeting["version"], if_match)
    scope.db.execute(
        delete(idempotency_records).where(
            idempotency_records.c.workspace_id == scope.workspace_id,
            idempotency_records.c.endpoint == f"chat:{meeting_id}",
        )
    )
    scope.db.execute(
        delete(chat_messages).where(
            chat_messages.c.workspace_id == scope.workspace_id,
            chat_messages.c.meeting_id == str(meeting_id),
        )
    )
    scope.db.execute(
        update(meetings)
        .where(meetings.c.id == str(meeting_id))
        .values(version=meetings.c.version + 1)
    )

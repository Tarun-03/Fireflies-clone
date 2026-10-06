from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from starlette.responses import Response

from app.api.dependencies import Scoped
from app.core.errors import DomainError
from app.core.limits import rate_limit
from app.schemas.common import StrictModel
from app.services.exports import blocks, parts, pdf_export, text_export

router = APIRouter(prefix="/api/v1/meetings")
Section = Literal["all", "transcript", "summary", "tasks"]


class ExportManifest(StrictModel):
    parts: int
    maximum_characters_per_part: int
    note: str


@router.get("/{meeting_id}/export/manifest", response_model=ExportManifest)
def manifest(
    meeting_id: UUID,
    scope: Scoped,
    section: Section = "all",
    timestamps: bool = True,
    speaker_names: bool = True,
) -> ExportManifest:
    content = parts(blocks(scope, str(meeting_id), section, timestamps, speaker_names))
    return ExportManifest(
        parts=len(content),
        maximum_characters_per_part=40000,
        note=(
            "Download every numbered part for the complete content. PDF u"
            "ses embedded DejaVu fonts; unsupported glyphs are explicit U"
            "nicode codes. TXT and Markdown preserve all original charact"
            "ers."
        ),
    )


@router.get("/{meeting_id}/export")
def export(
    meeting_id: UUID,
    scope: Scoped,
    format: Literal["txt", "md", "pdf"] = "txt",
    section: Section = "all",
    timestamps: bool = True,
    speaker_names: bool = True,
    part: int = Query(1, ge=1, le=200),
) -> Response:
    rate_limit(scope.session_id, "export", 30)
    content = parts(blocks(scope, str(meeting_id), section, timestamps, speaker_names))
    if part > len(content):
        raise DomainError(404, "not_found", "This export part does not exist.")
    selected = content[part - 1]
    payload = (
        pdf_export(selected, part, len(content))
        if format == "pdf"
        else text_export(selected, format == "md")
    )
    if len(payload) >= 4 * 1024 * 1024:
        raise DomainError(
            413,
            "export_too_large",
            "This PDF part exceeds the download allowance. Choose TXT or Markd"
            "own for complete content.",
        )
    media = {
        "txt": "text/plain; charset=utf-8",
        "md": "text/markdown; charset=utf-8",
        "pdf": "application/pdf",
    }[format]
    filename = f"meeting-part-{part}-of-{len(content)}.{format}"
    return Response(
        payload,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Parts": str(len(content)),
        },
    )

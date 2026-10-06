import io
import re
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate
from sqlalchemy import select

from app.api.annotations import stamp
from app.api.dependencies import Scope
from app.models import (
    action_items,
    meetings,
    participants,
    segments,
    speakers,
    summaries,
    summary_points,
)
from app.repositories.scoped import get_resource

Block = tuple[str, str]

_original_unicode_cmap = ttfonts.makeToUnicodeCMap


def unicode_cmap(fontname: str, subset: list[int]) -> str:
    # ReportLab 5.0.1 emits non-BMP destinations as code points. PDF requires UTF-16BE.
    return re.sub(
        r"(<[0-9A-F]{2}> )<([0-9A-F]{5,6})>",
        lambda match: (
            match[1] + "<" + chr(int(match[2], 16)).encode("utf-16-be").hex().upper() + ">"
        ),
        _original_unicode_cmap(fontname, subset),
    )


ttfonts.makeToUnicodeCMap = unicode_cmap


def blocks(
    scope: Scope, meeting_id: str, section: str, timestamps: bool, speaker_names: bool
) -> list[Block]:
    meeting = get_resource(scope, meetings, meeting_id)
    result: list[Block] = [
        ("title", meeting["title"]),
        (
            "meta",
            f"{meeting['occurred_at']} | {stamp(meeting['duration_ms'])} | "
            f"transcript revision {meeting['transcript_revision']}",
        ),
    ]
    if section in {"all", "summary"}:
        summary = (
            scope.db.execute(
                select(summaries).where(
                    summaries.c.meeting_id == meeting_id,
                    summaries.c.workspace_id == scope.workspace_id,
                )
            )
            .mappings()
            .one()
        )
        result.extend(
            [
                ("heading", "Meeting notes"),
                (
                    "meta",
                    f"Generated from transcript | {summary['provider']} | "
                    f"source revision {summary['source_revision']}",
                ),
                ("text", summary["overview"]),
            ]
        )
        points = scope.db.execute(
            select(summary_points)
            .where(
                summary_points.c.meeting_id == meeting_id,
                summary_points.c.workspace_id == scope.workspace_id,
            )
            .order_by(summary_points.c.kind, summary_points.c.position)
        ).mappings()
        for point in points:
            result.append(
                (
                    "text",
                    ("Decision: " if point["kind"] == "decision" else "Key point: ")
                    + point["text"],
                )
            )
        if summary["notes"]:
            result.extend([("heading", "Personal notes"), ("text", summary["notes"])])
    if section in {"all", "tasks"}:
        result.append(("heading", "Action items"))
        for task in scope.db.execute(
            select(action_items, participants.c.display_name.label("owner_name"))
            .outerjoin(participants, participants.c.id == action_items.c.assignee_participant_id)
            .where(
                action_items.c.workspace_id == scope.workspace_id,
                action_items.c.meeting_id == meeting_id,
            )
            .order_by(action_items.c.created_at, action_items.c.id)
        ).mappings():
            result.append(
                (
                    "text",
                    f"[{'x' if task['status'] == 'completed' else ' '}] {task['text']}"
                    + (f" | Owner: {task['owner_name']}" if task["owner_name"] else " | Unassigned")
                    + (f" | Due {task['due_date']}" if task["due_date"] else ""),
                )
            )
    if section in {"all", "transcript"}:
        result.append(("heading", "Transcript"))
        for row in scope.db.execute(
            select(segments, speakers.c.display_name)
            .join(speakers, speakers.c.id == segments.c.speaker_id)
            .where(
                segments.c.workspace_id == scope.workspace_id, segments.c.meeting_id == meeting_id
            )
            .order_by(segments.c.start_ms, segments.c.ordinal)
        ).mappings():
            prefix = (f"[{stamp(row['start_ms'])}] " if timestamps else "") + (
                row["display_name"] + ": " if speaker_names else ""
            )
            result.append(("text", prefix + row["text"]))
    return result


def parts(content: list[Block]) -> list[list[Block]]:
    result: list[list[Block]] = [[]]
    used = 0
    for kind, value in content:
        # Split long paragraphs as explicit continuations, without dropping characters.
        for start in range(0, max(1, len(value)), 2000):
            piece = value[start : start + 2000]
            if used + len(piece) > 40000:
                result.append([])
                used = 0
            result[-1].append((kind, piece))
            used += len(piece)
    return result


def text_export(content: list[Block], markdown: bool) -> bytes:
    def safe(value: str) -> str:
        if not markdown:
            return value
        value = escape(value)
        return re.sub(r"([\\`*_{}\[\]()#+.!|>~\-])", r"\\\1", value)

    lines = []
    for kind, value in content:
        prefix = (
            ("# " if kind == "title" else "## " if kind == "heading" else "") if markdown else ""
        )
        lines.append(prefix + safe(value))
    return ("\n\n".join(lines) + "\n").encode("utf-8")


@lru_cache(maxsize=1)
def load_fonts() -> set[int]:
    folder = Path(__file__).resolve().parents[2] / "assets" / "fonts"
    regular = TTFont("WorkspaceSans", str(folder / "DejaVuSans.ttf"))
    pdfmetrics.registerFont(regular)
    pdfmetrics.registerFont(TTFont("WorkspaceSansBold", str(folder / "DejaVuSans-Bold.ttf")))
    return set(regular.face.charToGlyph)


def pdf_export(content: list[Block], part: int, total: int) -> bytes:
    supported = load_fonts()
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=46,
        leftMargin=46,
        topMargin=48,
        bottomMargin=48,
        pageCompression=1,
        title="Meeting workspace export",
        author="Meeting workspace",
    )
    styles = {
        kind: ParagraphStyle(
            kind,
            fontName="WorkspaceSansBold" if kind in {"title", "heading"} else "WorkspaceSans",
            fontSize=20
            if kind == "title"
            else 13
            if kind == "heading"
            else 9
            if kind == "meta"
            else 10,
            leading=27 if kind == "title" else 18 if kind == "heading" else 15,
            textColor=colors.HexColor("#626673" if kind == "meta" else "#252331"),
            spaceAfter=12,
            wordWrap="CJK",
        )
        for kind in ["title", "heading", "text", "meta"]
    }
    unsupported = {
        ord(char)
        for _, value in content
        for char in value
        if ord(char) not in supported and char not in "\n\r\t"
    }

    def literal(value: str) -> str:
        displayed = "".join(
            char if ord(char) in supported or char in "\n\r\t" else f"[U+{ord(char):04X}]"
            for char in value
        )
        return escape(displayed).replace("\n", "<br/>")

    story: list[Flowable] = []
    if total > 1:
        story.append(
            Paragraph(
                f"Part {part} of {total}. Download every part for the complete export.",
                styles["meta"],
            )
        )
    if unsupported:
        story.append(
            Paragraph(
                "Characters outside the bundled font are shown as explicit Unicode"
                " codes. TXT and Markdown preserve all original characters.",
                styles["meta"],
            )
        )
    for kind, value in content:
        story.append(Paragraph(literal(value), styles[kind]))

    def footer(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("WorkspaceSans", 8)
        canvas.setFillColor(colors.HexColor("#626673"))
        canvas.drawString(46, 28, "Meeting workspace | Private export")
        canvas.drawRightString(A4[0] - 46, 28, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()

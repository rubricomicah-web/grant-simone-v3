import os
import re
from pathlib import Path
from typing import Iterable, List, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    HRFlowable,
    Table,
    TableStyle,
)

STORAGE = "storage/generated"
os.makedirs(STORAGE, exist_ok=True)


def slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", s or "proposal").strip("_")[:80] or "proposal"


def _register_arial_family() -> Tuple[str, str]:
    """Use Arial when available; otherwise use ReportLab's built-in Arial-compatible sans font.

    We do not bundle or expose font files. Railway/Linux images usually do not include Arial,
    so Helvetica is the safest built-in fallback for PDF rendering.
    """
    candidates = [
        ("Arial", "Arial-Bold", "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf", "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"),
        ("Arial", "Arial-Bold", "/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        ("Arial", "Arial-Bold", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("LiberationSans", "LiberationSans-Bold", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        ("DejaVuSans", "DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for regular_name, bold_name, regular_path, bold_path in candidates:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            try:
                if regular_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(regular_name, regular_path))
                if bold_name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                return regular_name, bold_name
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


BASE_FONT, BOLD_FONT = _register_arial_family()


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _clean_line(line: str) -> str:
    line = (line or "").strip()
    line = line.replace("**", "")
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = re.sub(r"^[-*]\s+", "• ", line)
    return line.strip()


def _is_heading(line: str) -> bool:
    raw = (line or "").strip()
    cleaned = _clean_line(raw)
    if not cleaned:
        return False
    if raw.startswith("#"):
        return True
    if cleaned.endswith(":") and len(cleaned) <= 80:
        return True
    common = {
        "executive summary",
        "organization overview",
        "applicant overview",
        "statement of need",
        "project description",
        "goals and objectives",
        "use of funds",
        "budget narrative",
        "expected impact",
        "sustainability plan",
        "evaluation plan",
        "timeline",
        "conclusion",
        "compliance checklist",
        "application narrative",
        "funding purpose",
    }
    return cleaned.lower().strip(":") in common


def _paragraph_chunks(body: str) -> List[Tuple[str, str]]:
    """Return [(kind, text)] where kind is heading, bullet, body, spacer, or pagebreak."""
    chunks: List[Tuple[str, str]] = []
    for raw in (body or "").replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            if chunks and chunks[-1][0] != "spacer":
                chunks.append(("spacer", ""))
            continue
        if re.match(r"^-{3,}$", line):
            chunks.append(("pagebreak", ""))
            continue
        cleaned = _clean_line(line)
        if _is_heading(line):
            chunks.append(("heading", cleaned.rstrip(":")))
        elif cleaned.startswith("•") or re.match(r"^(\d+\.|[a-zA-Z]\))\s+", cleaned):
            chunks.append(("bullet", cleaned))
        else:
            chunks.append(("body", cleaned))
    return chunks



def _title_parts(title: str) -> Tuple[str, str]:
    cleaned = title or "Grant Proposal"
    if " - " in cleaned:
        left, right = cleaned.split(" - ", 1)
        return left.strip() or "Applicant", right.strip() or "Funding Opportunity"
    return cleaned.strip(), "Funding Opportunity"


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setFont(BASE_FONT, 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(doc.leftMargin, 0.42 * inch, "Grant Proposal")
    canvas.drawRightString(width - doc.rightMargin, 0.42 * inch, f"Page {doc.page}")
    canvas.restoreState()


def proposal_pdf(title: str, body: str) -> str:
    """Create a clean proposal PDF with professional spacing and bold titles.

    Layout goals:
    - Letter page, proper margins
    - Arial when available, safe sans-serif fallback on Railway
    - Bold proposal title and section titles
    - Comfortable paragraph spacing and line height
    - No manual line drawing, so text wraps and page breaks safely
    """
    path = os.path.join(STORAGE, f"{slugify(title)}.pdf")

    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.72 * inch,
        title=title or "Grant Proposal",
        author="Applicant",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PremiumProposalTitle",
        parent=styles["Title"],
        fontName=BOLD_FONT,
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#102219"),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "PremiumProposalSubtitle",
        parent=styles["Normal"],
        fontName=BASE_FONT,
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#3A3A3A"),
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "PremiumProposalMeta",
        parent=styles["Normal"],
        fontName=BASE_FONT,
        fontSize=8.8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#666666"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "PremiumProposalHeading",
        parent=styles["Heading2"],
        fontName=BOLD_FONT,
        fontSize=13.5,
        leading=18,
        textColor=colors.HexColor("#123322"),
        spaceBefore=15,
        spaceAfter=7,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "PremiumProposalBody",
        parent=styles["BodyText"],
        fontName=BASE_FONT,
        fontSize=10.2,
        leading=16.2,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#222222"),
        spaceAfter=8,
    )
    bullet_style = ParagraphStyle(
        "PremiumProposalBullet",
        parent=body_style,
        leftIndent=18,
        firstLineIndent=-10,
        spaceAfter=5,
    )

    story = []
    applicant, opportunity = _title_parts(title or "Grant Proposal")
    story.append(Spacer(1, 0.35 * inch))
    story.append(Paragraph(_escape(title or "Grant Proposal"), title_style))
    story.append(Paragraph(_escape("Grant Proposal"), subtitle_style))
    story.append(Spacer(1, 0.18 * inch))
    story.append(HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#1F7A4D"), spaceBefore=3, spaceAfter=16))

    for kind, text in _paragraph_chunks(body):
        if kind == "pagebreak":
            story.append(PageBreak())
            continue
        if kind == "spacer":
            story.append(Spacer(1, 5))
            continue
        if kind == "heading":
            story.append(Paragraph(_escape(text), heading_style))
        elif kind == "bullet":
            story.append(Paragraph(_escape(text), bullet_style))
        else:
            story.append(Paragraph(_escape(text), body_style))

    if len(story) <= 4:
        story.append(Paragraph("No proposal content was generated. Please regenerate this proposal.", body_style))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return path

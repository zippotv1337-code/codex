from __future__ import annotations

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "FINAL_HANDOFF_CLAUDE_OWNER_ATWORK.md"
OUTPUT = ROOT / "output" / "pdf" / "CREATOR_OPS_FINAL_HANDOFF_CLAUDE_OWNER_ATWORK.pdf"


def font_setup() -> tuple[str, str, str]:
    font_dir = Path("C:/Windows/Fonts")
    regular, bold, mono = font_dir / "segoeui.ttf", font_dir / "segoeuib.ttf", font_dir / "consola.ttf"
    pdfmetrics.registerFont(TTFont("UI", regular))
    pdfmetrics.registerFont(TTFont("UI-Bold", bold))
    pdfmetrics.registerFont(TTFont("Mono", mono))
    return "UI", "UI-Bold", "Mono"


REGULAR, BOLD, MONO = font_setup()
NAVY = colors.HexColor("#173B36")
GREEN = colors.HexColor("#2F6B58")
CREAM = colors.HexColor("#F5F0E7")
INK = colors.HexColor("#222520")
MUTED = colors.HexColor("#65716B")
LINE = colors.HexColor("#D8D5CC")


def rich(text: str) -> str:
    value = html.escape(text.strip())
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r'<font name="Mono" size="8">\1</font>', value)
    return value


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleUI", fontName=BOLD, fontSize=23, leading=28, textColor=NAVY, spaceAfter=8))
styles.add(ParagraphStyle(name="SubUI", fontName=REGULAR, fontSize=9, leading=13, textColor=MUTED, spaceAfter=14))
styles.add(ParagraphStyle(name="H1UI", fontName=BOLD, fontSize=16, leading=20, textColor=NAVY, spaceBefore=12, spaceAfter=7))
styles.add(ParagraphStyle(name="H2UI", fontName=BOLD, fontSize=12, leading=15, textColor=GREEN, spaceBefore=10, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyUI", fontName=REGULAR, fontSize=9, leading=13, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="TableHeadUI", fontName=BOLD, fontSize=8.5, leading=11, textColor=colors.white))
styles.add(ParagraphStyle(name="BulletUI", fontName=REGULAR, fontSize=9, leading=13, textColor=INK, leftIndent=12, firstLineIndent=-7, bulletIndent=4, spaceAfter=3))
styles.add(ParagraphStyle(name="QuoteUI", fontName=REGULAR, fontSize=8.7, leading=13, textColor=NAVY, leftIndent=10, rightIndent=8, borderColor=GREEN, borderWidth=1, borderPadding=8, backColor=CREAM, spaceBefore=6, spaceAfter=8))
styles.add(ParagraphStyle(name="CodeUI", fontName=MONO, fontSize=7.7, leading=11, textColor=colors.HexColor("#EAF4EF"), backColor=NAVY, borderPadding=8, spaceBefore=4, spaceAfter=8))


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont(REGULAR, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Creator Ops - Finaler Handoff - 04.09.2026")
    canvas.drawRightString(192 * mm, 9 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def markdown_story(text: str) -> list:
    lines = text.splitlines()
    story: list = []
    index = 0
    in_code = False
    code_lines: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            if in_code:
                story.append(Paragraph("<br/>".join(html.escape(x) or " " for x in code_lines), styles["CodeUI"]))
                code_lines = []
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if line.startswith("| "):
            block: list[list[str]] = []
            while index < len(lines) and lines[index].startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip("|").split("|")]
                if not all(re.fullmatch(r"[-: ]+", cell) for cell in cells):
                    block.append(cells)
                index += 1
            data = [
                [Paragraph(rich(cell), styles["TableHeadUI"] if row_index == 0 else styles["BodyUI"]) for cell in row]
                for row_index, row in enumerate(block)
            ]
            table = Table(data, colWidths=[34 * mm, 51 * mm, 34 * mm, 55 * mm], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), BOLD), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), .4, LINE), ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 7)])
            continue
        if not line.strip():
            index += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(rich(line[2:]), styles["TitleUI"]))
        elif line.startswith("## "):
            story.append(Paragraph(rich(line[3:]), styles["H1UI"]))
        elif line.startswith("### "):
            story.append(Paragraph(rich(line[4:]), styles["H2UI"]))
        elif line.startswith("> "):
            quote = [line[2:]]
            index += 1
            while index < len(lines) and lines[index].startswith("> "):
                quote.append(lines[index][2:]); index += 1
            story.append(Paragraph(rich(" ".join(quote)), styles["QuoteUI"]))
            continue
        elif re.match(r"^\d+\. ", line):
            number, value = line.split(". ", 1)
            story.append(Paragraph(rich(value), styles["BulletUI"], bulletText=f"{number}."))
        elif line.startswith("- "):
            story.append(Paragraph(rich(line[2:]), styles["BulletUI"], bulletText="•"))
        else:
            paragraph = [line]
            index += 1
            while index < len(lines) and lines[index].strip() and not re.match(r"^(#|\-|\d+\.|>|\||```)", lines[index]):
                paragraph.append(lines[index]); index += 1
            story.append(Paragraph(rich(" ".join(paragraph)), styles["BodyUI"]))
            continue
        index += 1
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = BaseDocTemplate(
        str(OUTPUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=20 * mm,
        title="Creator Ops - Finaler Handoff für Claude, Owner und @work",
        author="Creator Ops",
    )
    frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="main")
    document.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=footer))
    story = markdown_story(SOURCE.read_text(encoding="utf-8"))
    story.insert(2, Table([[Paragraph("VERIFIZIERT", ParagraphStyle(name="Badge", fontName=BOLD, fontSize=8, textColor=colors.white, alignment=TA_CENTER))]], colWidths=[30 * mm], style=TableStyle([("BACKGROUND",(0,0),(-1,-1),GREEN),("BOX",(0,0),(-1,-1),0,GREEN),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)])))
    story.insert(3, Spacer(1, 7))
    document.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()

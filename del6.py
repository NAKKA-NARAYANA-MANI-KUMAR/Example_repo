from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase.pdfmetrics import stringWidth
import html
from urllib.parse import urlparse

# ---------------- Sample Helper Functions ---------------- #

def get_icon_path(name: str) -> str:
    # Stub: Normally you'd resolve icons from filesystem
    return name  

def svg_icon_fn(path, width=12, height=12):
    # Stub: You could integrate svglib if needed
    return ""

def _pill(styles, text, width, height):
    """Draw strength as styled Paragraph inside a colored pill."""
    return Paragraph(
        f'<para align="center" backColor="#E5F5F4" '
        f'borderColor="#00625B" borderWidth="0.5" borderRadius="5">'
        f'{text}</para>',
        ParagraphStyle("Pill", parent=styles["TableCell"], fontSize=8, textColor=colors.HexColor("#00625B"))
    )

# Dummy class for HyperlinkParagraph (simulate clickable links in ReportLab)
class HyperlinkParagraph(Paragraph):
    def __init__(self, text, url, style):
        super().__init__(f'<link href="{url}"><u>{html.escape(text)}</u></link>', style)

# ---------------- The Medications Table Builder ---------------- #

def build_medications_table(styles, metric, svg_icon_fn, medications: list) -> Table | None:
    if not medications:
        return None

    has_any_remarks = any(((med.get("instructions") or "").strip()) for med in medications)

    header_labels = ["", "Medications", "Start on", "Frequency", "Duration"]
    if has_any_remarks:
        header_labels.append("Remarks")
    headers = []
    for idx, h in enumerate(header_labels):
        align = "LEFT" if idx == 1 else "CENTER"
        headers.append(Paragraph(f'<para alignment="{align}">{h}</para>', styles["TableHeader"]))
    table_data = [headers]

    for i, med in enumerate(medications, 1):
        name = (med.get("name", "") or "").upper()
        external_url = med.get("external_url", "")

        def _sanitize_url(url: str) -> str | None:
            try:
                url = (url or "").strip()
                parsed = urlparse(url)
                if parsed.scheme not in {"http", "https"}:
                    return None
                if not parsed.netloc:
                    return None
                if any(ch in url for ch in ('"', "'", "<", ">", "\n", "\r")):
                    return None
                return url
            except Exception:
                return None

        safe_url = _sanitize_url(external_url)
        if safe_url:
            name_para = HyperlinkParagraph(
                name,
                safe_url,
                ParagraphStyle("LeftAlignedCell", parent=styles["TableCell"], alignment=TA_LEFT)
            )
        else:
            name_para = Paragraph(html.escape(name), ParagraphStyle("LeftAlignedCell", parent=styles["TableCell"], alignment=TA_LEFT))

        strength = med.get("strength", "")
        dosage = med.get("dosage", "")
        parts = dosage.split(" ")
        form = parts[1].lower() if len(parts) > 1 else ""
        form = "tablet" if form in {"tablets", "tablet"} else ("capsule" if form in {"capsules", "capsule"} else ("syrup" if form == "ml" else ("powder" if form in {"tsp", "tbsp"} else "")))
        start_from = med.get("start_from", "")
        start_from_cell = Paragraph(start_from, styles["TableCell"])

        if safe_url:
            supplement_cell = name_para
        else:
            supplement_flowables = []
            if strength or form or name:
                icon = ""
                if form:
                    candidate = get_icon_path(f"{form}.svg")
                    icon = svg_icon_fn(candidate, width=metric.get(form, {}).get("width", 12), height=metric.get(form, {}).get("height", 12))

                font_size = 8
                padding_top = 4
                padding_bottom = 4
                button_height = font_size + padding_top + padding_bottom
                text_width = stringWidth(strength, "Helvetica", 8)
                padding_left = 8
                padding_right = 8
                button_width = text_width + padding_left + padding_right

                pill = Paragraph("", styles["TableCell"]) if not strength else _pill(styles, strength, button_width, button_height)

                content_table = Table(
                    [[icon, "", name_para], ["", "", pill]],
                    colWidths=[15, 10, 136],
                )
                content_table.setStyle(
                    TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (2, -1), (2, -1), 4),
                    ])
                )
                supplement_flowables.append(content_table)

            supplement_cell = supplement_flowables if supplement_flowables else Paragraph("-", styles["TableCell"])

        frequency_raw = med.get("frequency", "")
        timing = med.get("timing", "")
        formatted_freq = ' <font color="#D9D9D9" size=10>•</font> '.join(frequency_raw.strip().split("-"))
        frequency_cell = Paragraph(f"{formatted_freq}<br/><font color='#667085'>{timing}</font>" if timing else formatted_freq, styles["TableCell"])

        duration_cell = Paragraph(med.get("duration", ""), styles["TableCell"])
        remarks_cell = Paragraph(med.get("instructions", ""), styles["TableCell"]) if med.get("instructions") else Paragraph("", styles["TableCell"])

        row = [
            Paragraph(f'<nobr><font size="7">{str(i).zfill(2)}</font></nobr>', styles["RowNumber"]),
            supplement_cell,
            start_from_cell,
            frequency_cell,
            duration_cell,
        ]
        if has_any_remarks:
            row.append(remarks_cell)
        table_data.append(row)

    if has_any_remarks:
        col_widths = [25, 181, 60, 70, 60, 135]
    else:
        col_widths = [25, 206, 100, 100, 100]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#00625B")),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (1, 1), (1, -1), "LEFT"),
        ("ALIGN", (2, 1), (2, -1), "CENTER"),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("ALIGN", (4, 1), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("TOPPADDING", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#e0e0e0")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.2, colors.HexColor("#00625B")),
    ]
    style.append(("ALIGN", (1, 0), (1, 0), "LEFT"))
    if has_any_remarks:
        style.append(("ALIGN", (5, 1), (5, -1), "CENTER"))

    for i in range(1, len(table_data), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F9FAFB")))

    table.setStyle(TableStyle(style))
    return table

# ---------------- PDF Generation ---------------- #

def build_pdf():
    doc = SimpleDocTemplate("medications_demo.pdf", pagesize=A4)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("TableHeader", fontSize=10, textColor=colors.HexColor("#00625B"), alignment=1, spaceAfter=6))
    styles.add(ParagraphStyle("TableCell", fontSize=9, leading=12))
    styles.add(ParagraphStyle("RowNumber", fontSize=8, alignment=1))

    medications = [
        {"name": "Paracetamol", "strength": "500mg", "dosage": "1 tablet", "start_from": "Today", "frequency": "Morning-Evening", "timing": "After food", "duration": "5 days", "instructions": "Take with water", "external_url": "https://example.com/paracetamol"},
        {"name": "Amoxicillin", "strength": "250mg", "dosage": "1 capsule", "start_from": "Tomorrow", "frequency": "Morning-Noon-Evening", "timing": "", "duration": "7 days", "instructions": "Complete the course", "external_url": ""},
    ]

    metric = {
        "tablet": {"width": 12, "height": 12},
        "capsule": {"width": 12, "height": 12},
    }

    story = [Paragraph("Medications Table", styles["Heading2"]), Spacer(1, 12)]
    table = build_medications_table(styles, metric, svg_icon_fn, medications)
    if table:
        story.append(table)
    doc.build(story)

if __name__ == "__main__":
    build_pdf()

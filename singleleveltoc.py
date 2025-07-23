import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, PageBreak, Spacer, Image,
    Table, TableStyle,Indenter
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle as PS
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === Colors ===
PMX_GREEN = colors.HexColor("#00625B")

# === Fonts ===
FONT_INTER_REGULAR = "Inter-Regular"
FONT_RALEWAY_MEDIUM = "Raleway-Medium"

# === Register Fonts (adjust paths as needed) ===
pdfmetrics.registerFont(TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_MEDIUM, "staticfiles/fonts/Raleway-Medium.ttf"))

# === Page Dimensions ===
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 40
RIGHT_MARGIN = 20
svg_dir = "staticfiles/icons/"

class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        self.allowSplitting = 0
        self.custom_toc_entries = []
        BaseDocTemplate.__init__(self, filename, pagesize=A4, **kwargs)
        frame = Frame(2.5 * cm, 2.5 * cm, 15 * cm, 25 * cm, id='F1')
        template = PageTemplate('normal', [frame])
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == "Heading1":
                self.custom_toc_entries.append((0, text, self.page))


class TOCDemoBuilder:
    def __init__(self, filename):
        self.filename = filename
        self.styles = getSampleStyleSheet()
        self.define_custom_styles()
        self.doc = MyDocTemplate(filename)

    def define_custom_styles(self):
        self.styles["Heading1"].fontSize = 30
        self.styles["Heading1"].leading = 34
        self.styles["Heading1"].spaceAfter = 12

        self.styles.add(PS(
            "TOCTitleStyle",
            fontName=FONT_RALEWAY_MEDIUM,
            fontSize=30,
            textColor=PMX_GREEN,
            leading=38,
            alignment=TA_LEFT,
        ))

        self.styles.add(PS(
            name="Body",
            fontSize=12,
            leading=16,
            fontName=FONT_INTER_REGULAR,
        ))

        self.styles.add(PS(
            name="TOCEntryText",
            fontName=FONT_INTER_REGULAR,
            fontSize=14,
            textColor=colors.HexColor("#002624"),
            leading=14,
        ))

        self.styles.add(PS(
            name="toc_pagenum",
            fontName=FONT_INTER_REGULAR,
            fontSize=20,
            leading=20,
            textColor=PMX_GREEN,
            alignment=TA_RIGHT
        ))

    def build_toc_table(self, toc_data):
        section = []
        
        toc_title = Paragraph("Table Of Contents", self.styles["TOCTitleStyle"])

        section.append(toc_title)
        section.append(Spacer(1, 12))
        section.append(Indenter(left=32, right=32))
        toc_table_data = []

        bullet_path = os.path.join("staticfiles", "icons", "table_content_bullet.png")

        if not toc_data:
            # Add dummy row to prevent crash
            toc_table_data.append([
                "", "", Paragraph("Generating TOC...", self.styles["TOCEntryText"]), ""
            ])
        else:
            for level, title, page in toc_data:
                icon_bullet = Image(bullet_path, width=40, height=40)
                toc_table_data.append([
                    icon_bullet,
                    Spacer(13, 1),
                    Paragraph(title, self.styles["TOCEntryText"]),
                    Paragraph(str(page), self.styles["toc_pagenum"]),
                ])

        toc_table = Table(toc_table_data, colWidths=[40, 13, 344, 134])
        toc_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            # ("VALIGN", (0, 0), (0, -1), "TOP"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (1, -1), "CENTER"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOX",(0,0),(-1,0),0.2,colors.black),
            ("BOX",(2,0),(2,0),0.2,colors.black),
            ("BOX",(0,1),(-1,1),0.2,colors.black),
            ("BOX",(0,2),(-1,2),0.2,colors.black)
        ]))
        
        section.append(toc_table)
        
        section.append(Indenter(left=-32, right=-32))
        section.append(PageBreak())
        return section

    def build_pdf(self):
        story = []

        # Add headings and body
        story.append(Paragraph("First Heading", self.styles["Heading1"]))
        story.append(Paragraph("Some content under first heading.", self.styles["Body"]))
        story.append(PageBreak())
        story.append(Paragraph("More content under third heading.", self.styles["Body"]))
        story.append(PageBreak())

        story.append(Paragraph("Second Heading", self.styles["Heading1"]))
        story.append(Paragraph("Some content under second heading.", self.styles["Body"]))
        story.append(PageBreak())
        story.append(Paragraph("More content under third heading.", self.styles["Body"]))
        story.append(PageBreak())

        story.append(Paragraph("Third Heading", self.styles["Heading1"]))
        story.append(Paragraph("More content under third heading.", self.styles["Body"]))
        story.append(PageBreak())

        self.doc.multiBuild(story)

        # Second pass: now insert the real TOC with correct alignment
        final_story = self.build_toc_table(self.doc.custom_toc_entries) + story
        self.doc.multiBuild(final_story)

if __name__ == "__main__":
    builder = TOCDemoBuilder("custom_toc_demo.pdf")
    builder.build_pdf()

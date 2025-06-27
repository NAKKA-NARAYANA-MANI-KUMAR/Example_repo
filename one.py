
import io
import os
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, send_file
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    Flowable,
    KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF, renderPM
from reportlab.lib import colors
from reportlab.lib.colors import Color
from svglib.svglib import svg2rlg

logger = logging.getLogger(__name__)

# Brand Colors
PMX_GREEN = colors.HexColor("#00625B")  # Primary brand color
PMX_GREEN_LIGHT = colors.HexColor("#EFE8CE")  # Secondary brand color
PMX_BUTTON_BG = colors.HexColor("#E6F4F3")  # Button background color
PMX_BACKGROUND = colors.HexColor("#F8F9FA")  # Page background color
PMX_TABLE_HEADER_BG = colors.HexColor("#f5f5f5")  # Table header background
PMX_TABLE_GRID = colors.HexColor("#e0e0e0")  # Table grid lines
PMX_TABLE_HEADER_BORDER = colors.HexColor("#d0d0d0")  # Table header border
PMX_TABLE_ALTERNATE_ROW = colors.HexColor("#F0F2F6")  # Alternating row color

# Font Configuration
FONT_FAMILY = "Inter"  # Base font family
FONT_INTER_LIGHT = "Inter-Light"  # Light weight
FONT_INTER_REGULAR = "Inter-Regular"  # Regular weight
FONT_INTER_BOLD = "Inter-Bold"  # Bold weight
FONT_INTER_MEDIUM="Inter-Medium"
# Typography Scale
FONT_SIZE_LARGE = 18  # Headers
FONT_SIZE_LARGE_MEDIUM = 16  # Headers
FONT_SIZE_MEDIUM = 12  # Subheaders
FONT_SIZE_SMALL = 10  # Supporting text
FONT_SIZE_BODY = 11  # Body text

# Layout Constants
PAGE_MARGIN = 0.3 * inch  # Standard page margin
TABLE_PADDING = 8  # Cell padding
TABLE_ROW_PADDING = 10  # Row padding
TABLE_HEADER_PADDING = 12  # Header row padding

# Table Column Width Ratios
TABLE_COL_NUMBER = 0.05  # Width ratio for number column
TABLE_COL_MAIN = 0.25  # Width ratio for main content columns
TABLE_COL_STANDARD = 0.15  # Width ratio for standard columns

# Available width for content (total width minus margins)
AVAILABLE_WIDTH = (8.5 * inch) - (1.5 * inch)
PAGE_WIDTH = A4[0]  # A4 width in points
LEFT_MARGIN = 40
RIGHT_MARGIN = 20
AVAILABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
# Default Doctor Information
DEFAULT_DOCTOR_NAME = "Dr. Samatha Tulla"
DEFAULT_SPECIALIZATION = "Internal Medicine Physician"
DEFAULT_ADDITIONAL_INFO = "& Diabetologist"
DEFAULT_REGISTRATION = "PMX-12345"

from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

pdfmetrics.registerFont(TTFont("Raleway-Medium", "staticfiles/fonts/Raleway-Medium.ttf"))

# ------------------------------------------------------------------------------
# Font Registration
# Register custom fonts for use in the PDF
pdfmetrics.registerFont(
    TTFont(FONT_INTER_LIGHT, "staticfiles/fonts/inter/Inter-Light.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_INTER_MEDIUM, "staticfiles/fonts/inter/Inter-Medium.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_INTER_BOLD, "staticfiles/fonts/inter/Inter-Bold.ttf")
)
pdfmetrics.registerFont(
    TTFont("Inter-Bold", "staticfiles/fonts/inter/Inter-Bold.ttf")
)


class PrescriptionOnlyPMXBasePage:
    """Base page class that provides common functionality for generating page content.
    Handles style initialization and base path setup for assets.
    """

    def __init__(self):
        # Initialize ReportLab's built-in styles
        self.styles = getSampleStyleSheet()
        # Set base path for static assets
        self.base_path = (
            Path(__file__).parent.parent.parent.parent.parent / "staticfiles" / "icons"
        )

    def generate(self, content_elements: list) -> list:
        """Generate the page content.

        Args:
            content_elements (list): List of ReportLab flowables to include in the page

        Returns:
            list: Combined list of flowables ready for PDF generation
        """
        elements = []
        elements.extend(content_elements)
        return elements

class PrescriptionOnlySVGImage(Flowable):
    """A custom flowable for handling SVG images in the PDF.
    Supports automatic scaling while maintaining aspect ratio.
    """

    def __init__(self, svg_path, width=None, height=None):
        """Args:
        svg_path (str): Path to the SVG file
        width (float, optional): Desired width for scaling
        height (float, optional): Desired height for scaling
        """
        super().__init__()
        # Convert SVG to ReportLab drawing
        self.filename = svg_path
        self.svg = svg2rlg(svg_path)
        self.svg_width = self.svg.width
        self.svg_height = self.svg.height

        # Calculate scaling based on provided dimensions
        if width is not None:
            scale = width / self.svg_width
            self.width = width
            self.height = self.svg_height * scale
        elif height is not None:
            scale = height / self.svg_height
            self.height = height
            self.width = self.svg_width * scale
        else:
            self.width = self.svg_width
            self.height = self.svg_height

        # Apply scaling to the SVG if dimensions were specified
        if width is not None or height is not None:
            self.svg.scale(self.width / self.svg_width, self.height / self.svg_height)

    def wrap(self, *args):
        """Return the scaled dimensions."""
        return (self.width, self.height)

    def draw(self):
        """Render the SVG on the PDF canvas."""
        renderPDF.draw(self.svg, self.canv, 0, 0)

class PrescriptionOnlyTemplate(PrescriptionOnlyPMXBasePage):
    """Base template for prescription pages. Handles header generation with logo,
    doctor information, and clinic address.
    """

    def __init__(self):
        super().__init__()
        # Reset base path for static assets if needed
        self.base_path = (
            Path(__file__).parent.parent.parent.parent.parent / "staticfiles" / "icons"
        )
        self.pmx_green = PMX_GREEN
        self.pmx_green_light = PMX_GREEN_LIGHT

    def _get_logo(self):
        """Load and return the clinic logo as an SVG image flowable.

        Returns:
            PrescriptionOnlySVGImage: Logo image sized appropriately for the header
        """
        # Try multiple possible paths for the logo
        possible_paths = [
            str(self.base_path / "pmx_health.svg"),
            str(
                Path(__file__).parent.parent.parent.parent.parent
                / "static"
                / "reports"
                / "pmx_health.svg"
            ),
            str(
                Path(__file__).parent.parent.parent.parent.parent
                / "staticfiles"
                / "reports"
                / "pmx_health.svg"
            ),
            str(
                Path(__file__).parent.parent.parent.parent.parent
                / "static"
                / "icons"
                / "pmx_health.svg"
            ),
            str(
                Path(__file__).parent.parent.parent.parent.parent
                / "staticfiles"
                / "icons"
                / "pmx_health.svg"
            ),
            "staticfiles/reports/pmx_health.svg",
            "static/reports/pmx_health.svg",
            "staticfiles/icons/pmx_health.svg",
            "static/icons/pmx_health.svg",
        ]

        for logo_path in possible_paths:
            try:
                if os.path.exists(logo_path):
                    # Try to load SVG
                    svg = svg2rlg(logo_path)
                    if svg is not None:
                        return PrescriptionOnlySVGImage(logo_path, width=60)
                    # If SVG loading failed, try to load as regular image
                    return Image(logo_path, width=60, height=60)
            except Exception:
                continue

        # If all attempts fail, return a placeholder text
        return Paragraph(
            "PMX Health",
            ParagraphStyle(
                "LogoPlaceholder",
                fontName=FONT_INTER_BOLD,
                fontSize=16,
                textColor=PMX_GREEN,
                alignment=TA_LEFT,
            ),
        )

class StyledDiagnosis(Flowable):
    def __init__(self, text, width=10 * mm, height=10 * mm):
        super().__init__()
        self.text = text
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c: canvas.Canvas = self.canv
        center_x = self.width / 2
        center_y = self.height / 2

        # Outer glow circle
        c.setFillColor(Color(0, 98/255, 91/255, alpha=0.1))
        c.circle(center_x, center_y, 5.2 * mm, fill=1, stroke=0)

        # Middle circle
        c.setFillColor(Color(0, 98/255, 91/255, alpha=0.2))
        c.circle(center_x, center_y, 3.1 * mm, fill=1, stroke=0)

        # Inner circle
        c.setFillColor(colors.HexColor("#00625B"))
        c.circle(center_x, center_y, 1.0 * mm, fill=1, stroke=0)


class PrescriptionPage(PrescriptionOnlyTemplate):
    """Generates a prescription PDF page with:
    - Header (logo, doctor info, address)
    - Patient information
    - Prescription details, diagnoses, lab recommendations, advice, and follow-up.
    """

    def __init__(self):
        super().__init__()
        # Initialize with standard margins
        self.PAGE_MARGIN = 0.25 * inch  # Use consistent margins
        self.init_styles()
        self.content_background_color = PMX_BACKGROUND
        logger.debug(
            "Initialized PrescriptionPage with margins: %.2f inches",
            self.PAGE_MARGIN / inch,
        )

    def init_styles(self):
        """Initialize all custom text styles used in the prescription."""

        
        
        # Prescription title style
        self.styles.add(
            ParagraphStyle(
                "PrescriptionTitle",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_LARGE,
                textColor=PMX_GREEN,
                leading=10,
                alignment=TA_LEFT,
                spaceBefore=10,
                spaceAfter=10,
                leftIndent=0,
            )
        )
        # Table cell style
        self.styles.add(
            ParagraphStyle(
                "TableCell",
                fontName=FONT_INTER_REGULAR,
                fontSize=8,
                textColor=PMX_GREEN,
                leading=12,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=0,
                wordWrap="CJK",
            )
        )
        
        self.styles.add(
            ParagraphStyle(
                "RowNumber",
                fontName=FONT_INTER_REGULAR,
                fontSize=12,
                textColor=PMX_GREEN,
                leading=12,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=0
            )
        )
        # Section title style
        self.styles.add(
            ParagraphStyle(
                "SectionTitle",
                fontName=FONT_INTER_BOLD,
                fontSize=FONT_SIZE_MEDIUM,
                textColor=colors.black,
                leading=16,
                alignment=TA_LEFT,
                spaceAfter=5,
            )
        )
        # Body text style
        self.styles.add(
            ParagraphStyle(
                "PMXBodyText",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_BODY,
                textColor=colors.black,
                leading=14,
                alignment=TA_LEFT,
                spaceAfter=3,
                leftIndent=10,
            )
        )
        # Italic text style
        self.styles.add(
            ParagraphStyle(
                "PMXItalicText",
                fontName=FONT_INTER_LIGHT,
                fontSize=FONT_SIZE_BODY,
                textColor=colors.gray,
                leading=14,
                alignment=TA_LEFT,
                spaceAfter=3,
                leftIndent=10,
            )
        )

        #TOCTitleStyle 
        self.styles.add(
            ParagraphStyle(
                name="TOCTitleStyle",
                fontName="Raleway-Medium",  # Registered above
                fontSize=30,
                textColor=PMX_GREEN,  # var(--Brand-500, #00625B)
                leading=38,           # matches line-height: 38px
                alignment=TA_LEFT,    # or TA_CENTER if you want centered TOC
                spaceAfter=12,
            )
        )

        #TOCEntryText
        self.styles.add(
            ParagraphStyle(
                name="TOCEntryText",
                fontName=FONT_INTER_REGULAR,  # Inter-Regular mapped earlier
                fontSize=10.5,                  # font-size: 14px
                textColor=PMX_GREEN,  # var(--Brand-900, #002624)
                leading=15,                   # line-height: 30px
                alignment=TA_LEFT,
                spaceAfter=6,                 # optional spacing between items
            )
        )

        #TOCEntryText
        self.styles.add(
            ParagraphStyle(
                name="TOCEntryTextt",
                fontName=FONT_INTER_REGULAR,  # Inter-Regular mapped earlier
                fontSize=11.5,                  # font-size: 14px
                textColor=PMX_GREEN,  # var(--Brand-900, #002624)
                leading=15,                   # line-height: 30px
                alignment=TA_LEFT,
                spaceAfter=6,                 # optional spacing between items
            )
        )

    def _build_styled_table(self, table_data, col_widths) -> Table:
        """Build a Table with a consistent style.
        This helper is used for both medications and therapies.

        Args:
            table_data (list): List of rows containing table data
            col_widths (list): List of column widths

        Returns:
            Table: Styled table ready for rendering
        """
        # Create inner table for remarks column when it contains multiple elements
        for row in table_data[1:]:  # Skip header row
            if isinstance(row[-1], list):
                remarks_data = [[elem] for elem in row[-1]]
                remarks_table = Table(remarks_data, colWidths=[col_widths[-1]])
                remarks_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ]
                    )
                )
                row[-1] = remarks_table

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style = [
            # Headers
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, 0), PMX_GREEN),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), FONT_INTER_BOLD),
            ("FONTSIZE", (0, 0), (-1, 0), FONT_SIZE_MEDIUM),
            ("BOTTOMPADDING", (0, 0), (-1, 0), TABLE_HEADER_PADDING),
            ("TOPPADDING", (0, 0), (-1, 0), TABLE_HEADER_PADDING),
            # Data rows
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),  # Number column
            ("ALIGN", (1, 1), (1, -1), "LEFT"),  # Medications column
            ("ALIGN", (2, 1), (2, -1), "CENTER"),  # Dosage column
            ("ALIGN", (3, 1), (3, -1), "CENTER"),  # Frequency column
            ("ALIGN", (4, 1), (4, -1), "CENTER"),  # Timing column
            ("ALIGN", (5, 1), (5, -1), "CENTER"),  # Duration column
            ("ALIGN", (6, 1), (6, -1), "CENTER"),  # Start From column
            ("ALIGN", (7, 1), (7, -1), "CENTER"),  # Remarks column
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), FONT_INTER_REGULAR),
            ("FONTSIZE", (0, 1), (-1, -1), FONT_SIZE_SMALL),
            ("TOPPADDING", (0, 1), (-1, -1), 15),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 15),
            ("LEFTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            ("RIGHTPADDING", (0, 0), (-1, -1), TABLE_PADDING),

            # Grid and Borders
            ("GRID", (0, 0), (-1, -1), 0.5, PMX_TABLE_GRID),
            ("LINEBELOW", (0, 0), (-1, 0), 1, PMX_TABLE_HEADER_BORDER),
            # Rounded Corners
            ("ROUNDEDCORNERS", [20, 20, 20, 20]),
            ("BOX", (0, 0), (-1, -1), 0.5, PMX_TABLE_GRID, None, None, "round"),
        ]

        # Add alternate row coloring starting from first data row (index 1)
        for i in range(1, len(table_data), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), PMX_TABLE_ALTERNATE_ROW))

        table.setStyle(TableStyle(style))
        return table

    

    def generate(self, data: dict) -> list:
        """Generate PDF content from JSON data."""
        logger.info("Generating prescription page")
        story = []

        # SVG bullet TOC section from your previous example
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph("Table Of Contents", self.styles["TOCTitleStyle"]))
        story.append(Spacer(1, 0.25 * cm))

        toc_items = data.get("toc_items", "")

        bullet_path = "staticfiles/icons/bullet_point_final.svg"
        toc_table_data = []
        for title, page in toc_items:
            pill = StyledDiagnosis(title) 
            toc_table_data.append([
                pill,
                Paragraph(title, self.styles["TOCEntryText"]),
                Paragraph(page, self.styles["TOCEntryText"])
            ])
            
        toc_table = Table(toc_table_data, colWidths=[1.2 * cm, 16.6 * cm, 1.0 * cm])
        toc_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (1, 0), (1, -1), "LEFT"),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))


        story.append(toc_table)

        # You can add more sections here based on your data
        return story

    
    def _add_logo_to_bottom_left(self, canvas, doc):
        """
        Draws the PMX logo at the bottom-left corner,
        adds 'www.pmxhealth.com' to its right,
        and adds doctor details above them on the last page.
        """
        logo_x = 30
        logo_y = 20
        text_padding = 370  # space between logo and website text
        logo_width = 0

        # ---- Doctor Info Above Footer ----
        canvas.setFont(FONT_INTER_LIGHT, 8)
        canvas.setFillColor(colors.black)
        doctor_text_y = logo_y + 50
       
        # ---- Logo Drawing ----
        logo = self._get_logo()
        if isinstance(logo, PrescriptionOnlySVGImage):
            drawing = svg2rlg(logo.filename)
            if drawing:
                logo_width = drawing.width
                renderPDF.draw(drawing, canvas, x=logo_x, y=logo_y)
        elif isinstance(logo, Image):
            logo_width = logo.drawWidth
            canvas.drawImage(
                logo.filename,
                x=logo_x,
                y=logo_y,
                width=logo.drawWidth,
                height=logo.drawHeight,
                mask='auto'
            )
        else:
            canvas.setFont(FONT_INTER_BOLD, 10)
            canvas.setFillColor(PMX_GREEN)
            fallback_text = "PMX Health"
            canvas.drawString(logo_x, logo_y, fallback_text)
            logo_width = canvas.stringWidth(fallback_text, FONT_INTER_BOLD, 10)

    
# ------------------ Flask App ------------------
app = Flask(__name__)

@app.route("/generate-prescription", methods=["POST"])
def generate_pdf():
    data = request.get_json()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer,
            pagesize=A4,
            leftMargin=30,     # adjust this to control left edge space
            rightMargin=20,
            topMargin=50,
            bottomMargin=50
            )
    template = PrescriptionPage()
    flowables = template.generate(data)

    doc.build(
        flowables,
        onFirstPage=template._add_logo_to_bottom_left,
        onLaterPages=template._add_logo_to_bottom_left
    )
    with open("output_from_buffer.pdf", "wb") as f:
        f.write(buffer.getvalue())

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="prescription.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)



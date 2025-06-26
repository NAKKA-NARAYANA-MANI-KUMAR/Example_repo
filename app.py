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
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF, renderPM

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


class FullPageWidthHRFlowable(Flowable):
    """
    Draws a horizontal line across the entire page width (ignoring margins).
    Works in any flowable frame by translating left, and drawing at safe Y-position.
    """

    def __init__(self, page_width, left_margin=72, thickness=1, color=colors.black, spaceAfter=5):
        super().__init__()
        self.page_width = page_width
        self.left_margin = left_margin
        self.thickness = thickness
        self.color = color
        self.spaceAfter = spaceAfter
        self.height = self.thickness + self.spaceAfter 

    def wrap(self, availWidth, availHeight):
        # Let the layout engine know how much vertical space this flowable takes
        return (availWidth, self.height)

    def draw(self):
        c = self.canv
        c.saveState()

        # Move canvas left to start at the absolute left edge of the page
        c.translate(self.left_margin-107.5, 0)

        # Draw the line slightly above the flowable base to avoid clipping
        y = self.thickness + 0.5  # Draw at 1.5 pts above the flowable's bottom

        c.setStrokeColor(PMX_TABLE_HEADER_BORDER)
        c.setLineWidth(self.thickness)
        c.line(0, y, self.page_width, y)

        c.restoreState()

class StyledAdditionalDiagnosis(Flowable):
    def __init__(self, diagnosis, styles, width=85 * mm, height=18 * mm):
        super().__init__()
        self.name = str(diagnosis["name"])
        self.location = diagnosis.get("location", "")
        self.styles = styles  # Save full stylesheet
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height
        
    def draw(self):
        c = self.canv
        radius = 10

        # Background box
        c.setStrokeColor(colors.HexColor("#D9E9E6"))
        c.setFillColor(colors.white)
        c.roundRect(0, 0, self.width, self.height, radius, stroke=1, fill=1)

        # Center points
        center_x = 6 * mm
        center_y = self.height / 2

        # Bullet layers
        c.setFillColor(colors.HexColor("#D0F0EE"))  # Outer glow
        c.circle(center_x, center_y, 4.0 * mm, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#71C1BD"))  # Middle circle
        c.circle(center_x, center_y, 2.8 * mm, fill=1, stroke=0)

        c.setFillColor(colors.white)  # White ring
        c.circle(center_x, center_y, 2.05 * mm, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#23968D"))  # Innermost dot
        c.circle(center_x, center_y, 2.0 * mm, fill=1, stroke=0)

        # Diagnosis name
        text_x = center_x + 4.5 * mm + 3 * mm
        text_y = self.height - 21  # From top

        c.setFont(FONT_INTER_REGULAR, 12)
        c.setFillColor(colors.HexColor("#00473C"))  # PMX_GREEN
        c.drawString(text_x, text_y, self.name)


        if self.location:
            tag_text = self.location.strip()
            font_size = 8
            padding_left = 8
            padding_right = 8

            # Calculate button width
            tag_text_width = stringWidth(tag_text, FONT_INTER_REGULAR, font_size)
            button_width = tag_text_width + padding_left + padding_right

            # Build Paragraph
            tag_para = Paragraph(tag_text, self.styles["PMXAvailableButton"])

            # Create Table
            tag_table = Table([[tag_para]], colWidths=[button_width])
            tag_table.setStyle(
                TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ])
            )

            # Render the table at desired location inside canvas
            tag_x = text_x
            tag_y = 3.5  # vertical offset from bottom

            w, h = tag_table.wrapOn(c, self.width, self.height)
            tag_table.drawOn(c, tag_x, tag_y)

class StyledDiagnosis(Flowable):
    def __init__(self, text, width=85 * mm, height=14 * mm):
        super().__init__()
        self.text = str(text['name'])  # Ensures it's always a string
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c: canvas.Canvas = self.canv
        radius = 17  # Rounded corner box

        # Rounded rectangle background
        c.setStrokeColor(colors.HexColor("#D9E9E6"))
        c.setFillColor(colors.white)
        c.roundRect(0, 0, self.width, self.height, radius, stroke=1, fill=1)

        # Bullet center position
        center_x = 6 * mm
        center_y = self.height / 2

        # 1. Outer glow circle – #D0F0EE
        c.setFillColor(colors.HexColor("#D0F0EE"))
        c.circle(center_x, center_y, 3.2 * mm, fill=1, stroke=0)

        # 2. Middle circle – #71C1BD
        c.setFillColor(colors.HexColor("#71C1BD"))
        c.circle(center_x, center_y, 2.3 * mm, fill=1, stroke=0)

        # 3. Thin white ring – #FFFFFF
        c.setFillColor(colors.white)
        c.circle(center_x, center_y, 1.65 * mm, fill=1, stroke=0)

        # 4. Innermost circle – #23968D
        c.setFillColor(colors.HexColor("#23968D"))
        c.circle(center_x, center_y, 1.6 * mm, fill=1, stroke=0)

        # Text in black
        c.setFillColor(PMX_GREEN)
        c.setFont(FONT_INTER_REGULAR, 12)
        text_x = center_x + 4.2 * mm + 3 * mm
        text_y = self.height / 2 - 3
        c.drawString(text_x, text_y, self.text)

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

class PrescriptionOnlyHRFlowable(Flowable):
    """A custom horizontal line flowable for visual separation between sections.
    Supports percentage-based widths and custom styling.
    """

    def __init__(self, width="100%", thickness=1, color=colors.black, spaceAfter=0):
        """Args:
        width (str|float): Line width, can be percentage (e.g. "100%") or absolute value
        thickness (int): Line thickness in points
        color (Color): Line color
        spaceAfter (int): Space to add after the line in points
        """
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color
        self.spaceAfter = spaceAfter
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        """Calculate dimensions based on available space.
        Handles percentage-based widths.
        """
        if isinstance(self.width, str) and self.width.endswith("%"):
            self.calcWidth = float(self.width[:-1]) * availWidth / 100.0
        else:
            self.calcWidth = self.width
        return (self.calcWidth, self.thickness + self.spaceAfter)

    def draw(self):
        """Draw the horizontal line on the canvas."""
        self.canv.setLineWidth(self.thickness)
        self.canv.setStrokeColor(self.color)
        self.canv.line(0, self.thickness, self.calcWidth, self.thickness)

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

    def _get_doctor_info(self, data) -> list:
        """Extract and format doctor information from the provided data.
        Falls back to default values if data is missing.

        Args:
            data (dict): Report data containing doctor information

        Returns:
            list: List of Paragraph flowables containing formatted doctor info
        """
        # Create styles for doctor information
        name_style = ParagraphStyle(
            "DoctorName",
            fontName=FONT_INTER_BOLD,
            fontSize=FONT_SIZE_MEDIUM,
            textColor=PMX_GREEN,
            leading=14,
            alignment=TA_LEFT,
        )
        credentials_style = ParagraphStyle(
            "Credentials",
            fontName=FONT_INTER_LIGHT,
            fontSize=FONT_SIZE_MEDIUM,
            textColor=PMX_GREEN,
            leading=14,
            alignment=TA_LEFT,
        )

        # Get doctor info directly from data
        doctor_info = data.get("doctor") if data else None

        # Build list of formatted paragraphs
        info = []

        if doctor_info:
            # Add doctor name
            doctor_name = doctor_info.get("name", "")
            if doctor_name:
                if not doctor_name.startswith("Dr."):
                    doctor_name = f"Dr. {doctor_name}"
                info.append(Paragraph(doctor_name, name_style))

            # Add specialization if available
            specialization = doctor_info.get("specialization")
            if specialization:
                info.append(Paragraph(specialization, credentials_style))

            # Add registration info if available
            registration = doctor_info.get(
                "registration_number", doctor_info.get("registration")
            )
            registration_state = doctor_info.get("registration_state")
            if registration:
                reg_text = f"Reg No: {registration}"
                if registration_state:
                    reg_text += f" ({registration_state})"
                info.append(Paragraph(reg_text, credentials_style))
            elif registration_state:
                info.append(
                    Paragraph(f"State: {registration_state}", credentials_style)
                )

        # If no doctor info was added, use defaults
        if not info:
            info = [
                Paragraph(DEFAULT_DOCTOR_NAME, name_style),
                Paragraph(DEFAULT_SPECIALIZATION, credentials_style),
                Paragraph(DEFAULT_ADDITIONAL_INFO, credentials_style),
            ]

        return info

    def _get_address(self, data) -> list:
        """Build the clinic address block with name and location details.

        Args:
            data (dict): Report data containing clinic information

        Returns:
            list: List of Paragraph flowables containing formatted address
        """
        # Default clinic information
        #clinic_name = "PMX Health"
        clinic_address_lines = [
            "PMX Health - 4th floor, Rd Number 44,",
            "Jubilee Hills, Hyderabad,",
            "Telangana - 500033",
        ]
        #mani
        # Check if we should use consultation data
        use_data_doctor = data and data.get("source_data", {}).get(
            "use_consultation_doctor", False
        )

        # Extract clinic info from data if available
        if (
            use_data_doctor
            and data
            and "report_info" in data
            and "clinic" in data["report_info"]
        ):
            clinic_info = data["report_info"]["clinic"]
            # if clinic_info.get("name"):
            #     clinic_name = clinic_info.get("name", clinic_name)
            if clinic_info.get("address"):
                address = clinic_info["address"]
                clinic_address_lines = address.split(", ")
                if len(clinic_address_lines) == 1:
                    clinic_address_lines = address.split(", ")

        # Create address style
        address_style = ParagraphStyle(
            "Address",
            fontName=FONT_INTER_LIGHT,
            fontSize=FONT_SIZE_SMALL,
            textColor=PMX_GREEN,
            leading=14,
            alignment=TA_RIGHT,
        )

        # Build list of formatted paragraphs
        address = []
        for line in clinic_address_lines:
            address.append(Paragraph(line, address_style))
        return address

    def _create_header(self, data=None) -> list:
        """Create the complete header section with logo, doctor info, and address.

        Args:
            data (dict): Report data containing header information

        Returns:
            list: List of flowables forming the complete header
        """
        elements = []
        logo = self._get_logo()
        doctor_info = self._get_doctor_info(data)
        address = self._get_address(data)

        # Arrange in a single-row table with three columns
        table_data = [[logo, doctor_info, address]]
        table = Table(table_data, colWidths=[60, 260, 180])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (0, -1), -20),
                    ("LEFTPADDING", (1, 0), (1, -1), 0),
                    ("LEFTPADDING", (2, 0), (2, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        -40,
                    ),  # Add negative top padding so that header of prescription page is aligned with the top of the page
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements.append(table)
        elements.append(Spacer(1, 10))
        # elements.append(
        #     PrescriptionOnlyHRFlowable(
        #         width="100%", thickness=0.5, color=PMX_GREEN, spaceAfter=5
        #     )
        # )

        elements.append(
            FullPageWidthHRFlowable(
                page_width=A4[0],        # A4 = 595.27 pts
                left_margin=72,          # Match your doc's leftMargin
                thickness=0.5,
                color=PMX_GREEN,
                spaceAfter=10
            )
        )
        elements.append(Spacer(1, 5))
        return elements

    def generate(self, data=None):
        """Generate the complete prescription page including header and content.

        Args:
            data (dict): Complete report data

        Returns:
            list: List of flowables forming the complete page
        """
        story = []
        story.extend(self._create_header(data))
        story.extend(self.generate_content(data))
        return story

    def generate_content(self, data):
        """Placeholder for content generation; to be overridden in subclass.

        Args:
            data (dict): Report data for content generation

        Returns:
            list: Empty list by default
        """
        return []


# ------------------ Subclass with Content ------------------

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

        #PrescriptionEnds here
        self.styles.add(
            ParagraphStyle(
                "PrescriptionEnds",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_SMALL,
                textColor=colors.gray,
                leading=10,
                alignment=TA_CENTER,  
                spaceBefore=10,
                spaceAfter=10,
                leftIndent=0,
            )
        )
        # Patient name style
        self.styles.add(
            ParagraphStyle(
                "PatientName",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_LARGE,
                textColor=PMX_GREEN,
                leading=10,
                alignment=TA_LEFT,
                spaceBefore=10,
                spaceAfter=10,
                leftIndent=0,
                rightIndent=0,
            )
        )
        # Date style
        self.styles.add(
            ParagraphStyle(
                "DateStyle",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_MEDIUM,
                textColor=PMX_GREEN,
                leading=20,
                alignment=TA_LEFT,
                spaceAfter=5,
            )
        )
        # Patient info style
        self.styles.add(
            ParagraphStyle(
                "PatientInfo",
                fontName=FONT_INTER_LIGHT,
                fontSize=FONT_SIZE_LARGE,
                textColor=PMX_GREEN,
                leading=10,
                alignment=TA_LEFT,
                spaceBefore=10,
                spaceAfter=10,
            )
        )
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
        # Table header style
        self.styles.add(
            ParagraphStyle(
                "TableHeader",
                fontName=FONT_INTER_BOLD,
                fontSize=FONT_SIZE_SMALL,
                textColor=PMX_GREEN,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=5,
                spaceAfter=3,
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
        # self.styles.add(
        #     ParagraphStyle(
        #         name="RowNumber",
        #         fontName="Courier",        # Monospaced font
        #         fontSize=9,                # Bigger for visibility
        #         alignment=TA_CENTER,
        #         textColor=PMX_GREEN,
        #         leading=12,
        #         spaceBefore=0,
        #         spaceAfter=0
        #     )
        # )
        # Row number style - prevents character splitting
        self.styles.add(
            ParagraphStyle(
                "RowNumber",
                fontName=FONT_INTER_REGULAR,
                fontSize=8,
                textColor=PMX_GREEN,
                leading=12,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=0,
                wordWrap=None,
                keepWithNext=True,
                allowOrphans=0
                #wordWrap="LTR",  # Use LTR to prevent character splitting
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
        # Button style
        self.styles.add(
            ParagraphStyle(
                "PMXButton",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_SMALL,
                textColor=colors.white,
                leading=12,
                alignment=TA_CENTER,
                backColor=PMX_GREEN,
                borderPadding=6,
                borderRadius=10,
                borderWidth=0,
                spaceAfter=0,
                spaceBefore=0,
            )
        )
        # Available button style
        self.styles.add(
            ParagraphStyle(
                "PMXAvailableButton",
                parent=self.styles["TableCell"],
                fontName=FONT_INTER_REGULAR,
                fontSize=8,
                textColor=PMX_GREEN,
                alignment=TA_CENTER,
                backColor=PMX_BUTTON_BG,
                borderPadding=3,
                borderRadius=10,
                borderWidth=0.5,
                borderColor=PMX_GREEN,
                leading=10,
                wordWrap="LTR",  # Prevent text wrapping
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

    def _create_patient_info(self, data: dict) -> list:
        """Create the patient information section with name, age, gender, and date."""
        elements = []
        user_profile = data.get("user_profile", {})

        logger.info(f"User profile data: {json.dumps(user_profile, default=str)}")

        # Get name
        first_name = user_profile.get("first_name", "")
        last_name = user_profile.get("last_name", "")
        name = f"{first_name} {last_name}".strip() or "No Name"

        # Get age and gender
        age = user_profile.get("age", "")
        gender = user_profile.get("gender", "")

        # Format the combined text
        if age and gender:
            combined_text = f"{name} <font size=9>{age} , {gender}</font>"
        elif age:
            combined_text = f"{name} <font size=9>{age} </font>"
        elif gender:
            combined_text = f"{name} <font size=9>{gender}</font>"
        else:
            combined_text = name

        logger.info(f"Patient info text: {combined_text}")

        current_date = datetime.now().strftime("%d/%m/%Y")

        name_date_data = [
            [
                Paragraph(combined_text, self.styles["PatientName"]),
                Paragraph(f"Date: {current_date}", self.styles["DateStyle"]),
            ]
        ]
        
        name_date_table = Table(
            name_date_data, colWidths=[AVAILABLE_WIDTH * 0.75, AVAILABLE_WIDTH * 0.25]
        )
        name_date_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )

        elements.append(name_date_table)
        elements.append(Spacer(1, 5))
        return elements

    def _create_prescription_table(self, medications: list) -> Table:
        """
        Builds the prescription table styled as per the provided screenshot.
        Only 6 columns: Number, Supplements, Dose, Frequency, Duration, Remarks.
        """
        if not medications:
            return None

        # Header row
        headers = [
            Paragraph(h, self.styles["TableHeader"])
            for h in ["", "Medications", "Dose", "Frequency", "Duration", "Remarks"]
        ]
        table_data = [headers]

        for i, med in enumerate(medications, 1):
            name = med.get("name", "")
            strength = med.get("strength", "")
            active_ingredients = med.get("active_ingredients", "")
            supplement_flowables = []
            # Supplement name with strength or type below (like Mixed, 500 mg)
            if strength or active_ingredients:
                supplement_text = f'<font name="Inter-Bold" >{name.upper()}</font>\n<font size=8>{strength or active_ingredients}</font>' 
                if name:
                    supplement_flowables.append(
                        Paragraph(name, self.styles["TableCell"])
                    )
                if strength:

                    # Calculate text width
                    text_width = stringWidth(strength, FONT_INTER_REGULAR, 8)

                    padding_left = 8
                    padding_right = 8
                    button_width = text_width + padding_left + padding_right

                    button = Paragraph(f"{strength}", self.styles["PMXAvailableButton"])

                    # Create a table with the computed width
                    button_table = Table([[button]], colWidths=[button_width])                    
                    button_table.setStyle(
                        TableStyle([
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ])
                    )
                    supplement_flowables.append(button_table)

                
            else:
                supplement_text = f'<b>{name.upper()}</b>'
            
            supplement_cell = supplement_flowables if supplement_flowables else Paragraph(supplement_text, self.styles["TableCell"])

            dosage = med.get("dosage", "")
            dose_cell = Paragraph(dosage, self.styles["TableCell"])

            frequency_raw = med.get("frequency", "")
            timing = med.get("timing", "")

            def format_frequency_with_gray_dots(frequency: str) -> str:
                parts = frequency.strip().split("-")
                # Insert gray dot between values
                return ' <font color="#CCCCCC">•</font> '.join(parts)
            
            if timing:
                combined_text = f"{format_frequency_with_gray_dots(frequency_raw)}<br/><font color='#4D4D4D'>{timing}</font>"
                frequency_cell = Paragraph(combined_text, self.styles["TableCell"])
            else:
                frequency_cell = Paragraph(format_frequency_with_gray_dots(frequency_raw), self.styles["TableCell"])


            duration_cell = Paragraph(med.get("duration", ""), self.styles["TableCell"])

            instructions = med.get("instructions", "")
            available_in_clinic = med.get("available_in_clinic", False)
            external_url = med.get("external_url","")
            remarks_flowables = []
            if instructions:
                remarks_flowables.append(
                    Paragraph(instructions, self.styles["TableCell"])
                )
            if available_in_clinic:
                button = Paragraph("Available at PMX", self.styles["PMXAvailableButton"])
            else:
                button = Paragraph(f'<link href="{external_url}">Buy Now</link>', self.styles["PMXAvailableButton"])
            button_table = Table([[button]], colWidths=[90])
            button_table.setStyle(
                TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ])
            )
            remarks_flowables.append(button_table)

            remarks_cell = remarks_flowables if remarks_flowables else Paragraph("", self.styles["TableCell"])

            row = [
                Paragraph(f'<nobr><font size="8">{str(i).zfill(2)}</font></nobr>', self.styles["RowNumber"]),
                supplement_cell,
                dose_cell,
                frequency_cell,
                duration_cell,
                remarks_cell,
            ]

            table_data.append(row)

        # Set 6 column widths matching the layout in the screenshot
        col_widths = [
            0.055 * AVAILABLE_WIDTH,  # Number
            0.30 * AVAILABLE_WIDTH,  # Supplements
            0.13 * AVAILABLE_WIDTH,  # Dose
            0.17 * AVAILABLE_WIDTH,  # Frequency
            0.13 * AVAILABLE_WIDTH,  # Duration
            0.22 * AVAILABLE_WIDTH,  # Remarks
        ]


        return self._build_styled_table(table_data, col_widths)


    def _create_therapies_table(self, therapies: list) -> Table:
        """Build the therapies table.

        Args:
            therapies (list): List of therapy dictionaries with the following structure:
            [
                {
                    "name": "Therapy Name",
                    "dose": "10mg",
                    "frequency": "Twice daily",
                    "duration": "7 days",
                    "instructions": "Special instructions"
                },
                ...
            ]

        Returns:
            Table: Styled table containing therapy information
        """
        if not therapies:
            return None

        # Get the full page width (A4 width)
        FULL_PAGE_WIDTH = A4[0] - 5 * self.PAGE_MARGIN

        headers = [
            Paragraph(h, self.styles["TableHeader"])
            for h in ["", "Therapy", "Frequency", "Duration", "Instructions", "Notes"]
        ]
        table_data = [headers]

        for i, therapy in enumerate(therapies, 1):
            row = [
                Paragraph(str(i), self.styles["RowNumber"]),
                Paragraph(therapy.get("name", ""), self.styles["TableCell"]),
                Paragraph(therapy.get("frequency", ""), self.styles["TableCell"]),
                Paragraph(therapy.get("duration", ""), self.styles["TableCell"]),
                Paragraph(therapy.get("instructions", ""), self.styles["TableCell"]),
                Paragraph(therapy.get("notes", ""), self.styles["TableCell"]),
            ]
            table_data.append(row)

        # Use full page width for column calculations
        col_widths = [
            0.05 * FULL_PAGE_WIDTH * 1.5,  # Number column (increased by 50%)
            0.25 * FULL_PAGE_WIDTH,  # Therapy name column (25%)
            0.15 * FULL_PAGE_WIDTH,  # Frequency column (15%)
            0.15 * FULL_PAGE_WIDTH,  # Duration column (15%)
            0.20 * FULL_PAGE_WIDTH,  # Instructions column (20%)
            0.20 * FULL_PAGE_WIDTH,  # Notes column (20%)
        ]
        return self._build_styled_table(table_data, col_widths)

    def _create_diagnosis(self, diagnoses: list) -> Table:
        # Create styled pills
        pills = [StyledDiagnosis(text) for text in diagnoses]

        # Build rows of 2 pills each
        rows = []
        for i in range(0, len(pills), 2):
            row = pills[i:i+2]
            if len(row) < 2:
                row.append(Spacer(85 * mm, 14 * mm))
            rows.append(row)

        # Create table
        table = Table(rows, colWidths=[90 * mm, 90 * mm], hAlign='LEFT')
        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        return table  
    
    def _create_additional_diagnosis(self, diagnoses: list) -> Table:
        # Create styled pills
        pills = [StyledAdditionalDiagnosis(text, self.styles) for text in diagnoses]

        # Build rows of 2 pills each
        rows = []
        for i in range(0, len(pills), 2):
            row = pills[i:i+2]
            if len(row) < 2:
                row.append(Spacer(85 * mm, 14 * mm))
            rows.append(row)

        # Create table
        table = Table(rows, colWidths=[90 * mm, 90 * mm], hAlign='LEFT')
        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))

        return table


    def _create_additional_sections(self, data: dict) -> list:
        """Create additional sections of the prescription."""
        elements = []

        # Process sections in order
        sections_to_process = [
            ("symptoms", "Symptoms:", None),
            ("signs", "Signs:", None),
            ("diagnoses", "Diagnoses:", None),
            ("lab_recommendations", "Advanced Investigation Recommendations:", None),
            ("advices", "Advice:", None),
        ]

        for section_key, title, custom_handler in sections_to_process:
            section_data = []

            # Try direct access
            if section_key in data and data.get(section_key):
                section_data = data.get(section_key, [])
            # Try nested reference_data
            elif "consultation" in data and "reference_data" in data.get(
                "consultation", {}
            ):
                ref_section = (
                    data.get("consultation", {})
                    .get("reference_data", {})
                    .get(section_key, [])
                )
                if ref_section:
                    # Extract just the names
                    section_data = [
                        item.get("name", "") for item in ref_section if "name" in item
                    ]

            if section_data:
                elements.append(Paragraph(title, self.styles["PrescriptionTitle"]))
                elements.append(Spacer(1, self.PAGE_MARGIN / 4))

                if custom_handler:
                    # Use custom handler for special sections like therapies
                    table = custom_handler(section_data)
                    if table:
                        elements.append(table)
                else:
                    # Standard bullet point list for other sections
                    for item in section_data:
                        if isinstance(item, dict) and "name" in item:
                            elements.append(
                                Paragraph(
                                    f"• {item['name']}", self.styles["PMXBodyText"]
                                )
                            )
                        else:
                            elements.append(
                                Paragraph(f"• {item}", self.styles["PMXBodyText"])
                            )

                elements.append(Spacer(1, self.PAGE_MARGIN / 4))

        # Handle follow-up data
        follow_up = self._get_follow_up_data(data)
        if follow_up:
            elements.extend(self._create_follow_up_section(follow_up))

        # Handle notes and instructions
        notes = self._get_notes_data(data)
        if notes:
            elements.extend(self._create_notes_section(notes))

        return elements

    def _get_follow_up_data(self, data: dict) -> dict:
        """Get follow-up data from various sources."""
        follow_up = {}
        if "follow_up" in data and data.get("follow_up"):
            follow_up = data.get("follow_up", {})
        elif "consultation" in data:
            follow_up_date = data.get("consultation", {}).get("follow_up_date")
            follow_up_notes = data.get("consultation", {}).get("follow_up_notes")
            if follow_up_date or follow_up_notes:
                follow_up = {
                    "next_visit_on": follow_up_date.split("T")[0]
                    if follow_up_date
                    else "",
                    "notes": follow_up_notes,
                }
        return follow_up

    def _create_follow_up_section(self, follow_up: dict) -> list:
        """Create the follow-up section."""
        elements = []
        if follow_up.get("next_visit_on", "") or follow_up.get("notes", ""):
            elements.append(Paragraph("Follow-up:", self.styles["PrescriptionTitle"]))
            if follow_up.get("next_visit_on", ""):
                elements.append(
                    Paragraph(
                        f"Next visit on: {follow_up.get('next_visit_on')}",
                        self.styles["PMXBodyText"],
                    )
                )
            if follow_up.get("notes", ""):
                elements.append(
                    Paragraph(
                        f"Notes: {follow_up.get('notes')}", self.styles["PMXBodyText"]
                    )
                )
            elements.append(Spacer(1, self.PAGE_MARGIN / 4))
        return elements

    def _get_notes_data(self, data: dict) -> dict:
        """Get notes and instructions data."""
        notes = {}

        # Get public notes
        if "public_notes" in data and data.get("public_notes"):
            notes["public_notes"] = data.get("public_notes", {}).get("notes")
        elif "consultation" in data and data.get("consultation", {}).get(
            "public_notes"
        ):
            notes["public_notes"] = data.get("consultation", {}).get("public_notes")

        # Get instructions
        if "instructions" in data and data.get("instructions"):
            notes["instructions"] = data.get("instructions", {}).get("instructions")
        elif "consultation" in data and data.get("consultation", {}).get(
            "instructions"
        ):
            notes["instructions"] = data.get("consultation", {}).get("instructions")

        return notes

    def _create_notes_section(self, notes: dict) -> list:
        """Create the notes and instructions section."""
        elements = []

        if notes.get("public_notes"):
            elements.append(
                Paragraph("Past Medical History:", self.styles["PrescriptionTitle"])
            )
            elements.append(
                Paragraph(notes["public_notes"], self.styles["PMXBodyText"])
            )
            elements.append(Spacer(1, self.PAGE_MARGIN / 4))

        if notes.get("instructions"):
            elements.append(
                Paragraph("Instructions:", self.styles["PrescriptionTitle"])
            )
            elements.append(
                Paragraph(notes["instructions"], self.styles["PMXBodyText"])
            )
            elements.append(Spacer(1, self.PAGE_MARGIN / 4))

        return elements

    def generate(self, data: dict) -> list:
        """Generate the full prescription page with proper margins and footer.

        Args:
            data (dict): Complete report data

        Returns:
            list: List of flowables forming the complete page
        """
        logger.info("Generating prescription page")
        logger.info(
            "Input data structure: %s", json.dumps(data.keys(), indent=2, default=str)
        )

        if "source_data" not in data and "report_info" in data:
            data["source_data"] = {}

        # Ensure we're using the content template
        story = []

        # Add header and content with proper spacing
        story.extend(self._create_header(data))
        story.append(Spacer(1, self.PAGE_MARGIN / 2))  # Add space after header

        # Add patient info
        story.extend(self._create_patient_info(data))

        # Add prescription title
        story.append(Paragraph("Prescription", self.styles["PrescriptionTitle"]))
        story.append(Spacer(1, self.PAGE_MARGIN / 4))

        # Handle medications from different possible sources
        medications = []
        if "medications" in data:
            # Direct access
            medications = data.get("medications", [])
        elif "consultation" in data and "reference_data" in data.get(
            "consultation", {}
        ):
            # From consultation reference_data
            ref_medications = (
                data.get("consultation", {})
                .get("reference_data", {})
                .get("medications", [])
            )
            for med in ref_medications:
                medications.append(
                    {
                        "name": med.get("name", ""),
                        "strength": med.get("strength", ""),
                        "dosage": med.get("dosage", ""),
                        "frequency": med.get("frequency", ""),
                        "duration": med.get("duration", ""),
                        "instructions": med.get("instructions", ""),
                        "active_ingredients": med.get("active_ingredients", ""),
                        "start_from": med.get("start_from", ""),
                        "timing": med.get("timing", ""),
                        "available_in_clinic": med.get("available_in_clinic", ""),
                        "external_url": med.get("external_url", ""),
                    }
                )

        if medications:
            story.append(self._create_prescription_table(medications))
            story.append(Spacer(1, self.PAGE_MARGIN / 4))
        
        # Handle therapies from different possible sources
        therapies = []
        if "therapies" in data:
            # Direct access
            therapies = data.get("therapies", [])
        elif "consultation" in data and "reference_data" in data.get(
            "consultation", {}
        ):
            # From consultation reference_data
            ref_therapies = (
                data.get("consultation", {})
                .get("reference_data", {})
                .get("therapies", [])
            )
            for therapy in ref_therapies:
                therapies.append(
                    {
                        "name": therapy.get("name", ""),
                        "type": therapy.get("therapy_type", ""),
                        "notes": therapy.get("notes", ""),
                    }
                )

        if therapies:
            story.append(Paragraph("Therapies:", self.styles["PrescriptionTitle"]))
            story.append(Spacer(1, self.PAGE_MARGIN / 4))
            story.append(self._create_therapies_table(therapies))
            story.append(Spacer(1, self.PAGE_MARGIN / 4))
        if therapies or medications:
            story.append(Paragraph("prescription ends here", self.styles["PrescriptionEnds"]))
            story.append(Spacer(1, self.PAGE_MARGIN / 4))
        # Extract diagnosis section first
        diagnosis_elements = []
        diagnosis_data = []

        # Try direct access
        if "diagnoses" in data and data.get("diagnoses"):
            diagnosis_data = data.get("diagnoses", [])
        # Try nested reference_data
        elif "consultation" in data and "reference_data" in data.get(
            "consultation", {}
        ):
            ref_diagnosis = (
                data.get("consultation", {})
                .get("reference_data", {})
                .get("diagnoses", [])
            )
            if ref_diagnosis:
                # Extract just the names
                diagnosis_data = [
                    item.get("name", "") for item in ref_diagnosis if "name" in item
                ]

        if diagnosis_data:
            diagnosis_elements.append(
                Paragraph("Diagnoses:", self.styles["PrescriptionTitle"])
            )
            diagnosis_elements.append(Spacer(1, self.PAGE_MARGIN / 4))

            diagnosis_elements.append(self._create_diagnosis(diagnosis_data))
            diagnosis_elements.append(Spacer(1, self.PAGE_MARGIN / 4))
        # Add diagnosis section first
        #story.extend(diagnosis_elements)
        story.append(KeepTogether(diagnosis_elements))
        additional_diagnosis_elements = []
        additional_diagnosis_data = []

        # Try direct access
        if "additional_diagnoses" in data and data.get("additional_diagnoses"):
            additional_diagnosis_data = data.get("additional_diagnoses", [])

        if additional_diagnosis_data:
            additional_diagnosis_elements.append(
                Paragraph("Additional Diagnoses:", self.styles["PrescriptionTitle"])
            )
            additional_diagnosis_elements.append(Spacer(1, self.PAGE_MARGIN / 4))

            additional_diagnosis_elements.append(self._create_additional_diagnosis(additional_diagnosis_data))
            additional_diagnosis_elements.append(Spacer(1, self.PAGE_MARGIN / 4))
        # Add diagnosis section first
        story.append(KeepTogether(additional_diagnosis_elements))

        # Add other additional sections (excluding diagnoses which we already added)
        other_sections = self._create_other_sections(data)
        story.extend(other_sections)

        # Handle follow-up data
        follow_up = self._get_follow_up_data(data)
        if follow_up:
            story.extend(self._create_follow_up_section(follow_up))

        # Handle notes and instructions
        notes = self._get_notes_data(data)
        if notes:
            story.extend(self._create_notes_section(notes))

        # Remove the spacer at the bottom that's causing the empty page
        logger.info("Prescription page generation complete")


        return story

    def _create_other_sections(self, data: dict) -> list:
        """Create additional sections of the prescription excluding diagnoses."""
        elements = []

        # Process sections in order (excluding diagnoses which is handled separately)
        sections_to_process = [
            ("symptoms", "Symptoms:", None),
            ("signs", "Signs:", None),
            ("lab_recommendations", "Advanced Investigation Recommendations:", None),
            ("advices", "Advice:", None),
        ]

        for section_key, title, custom_handler in sections_to_process:
            section_data = []

            # Try direct access
            if section_key in data and data.get(section_key):
                section_data = data.get(section_key, [])
            # Try nested reference_data
            elif "consultation" in data and "reference_data" in data.get(
                "consultation", {}
            ):
                ref_section = (
                    data.get("consultation", {})
                    .get("reference_data", {})
                    .get(section_key, [])
                )
                if ref_section:
                    # Extract just the names
                    section_data = [
                        item.get("name", "") for item in ref_section if "name" in item
                    ]

            if section_data:
                elements.append(Paragraph(title, self.styles["PrescriptionTitle"]))
                elements.append(Spacer(1, self.PAGE_MARGIN / 4))

                if custom_handler:
                    # Use custom handler for special sections like therapies
                    table = custom_handler(section_data)
                    if table:
                        elements.append(table)
                else:
                    # Standard bullet point list for other sections
                    for item in section_data:
                        if isinstance(item, dict) and "name" in item:
                            elements.append(
                                Paragraph(
                                    f"• {item['name']}", self.styles["PMXBodyText"]
                                )
                            )
                        else:
                            elements.append(
                                Paragraph(f"• {item}", self.styles["PMXBodyText"])
                            )

                elements.append(Spacer(1, self.PAGE_MARGIN / 4))

        return elements

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
        canvas.setFont(FONT_INTER_MEDIUM, 8)
        canvas.drawString(logo_x, doctor_text_y, "Dr. Samatha Tulla (MBBS, MD Internal Medicine)")
        canvas.setFont(FONT_INTER_LIGHT, 8)
        canvas.drawString(logo_x, doctor_text_y - 12, "Reg no: 68976 Telangana State Medical Council")

        # ---- Optional Signature Image (above doctor info) ----
        try:
            signature_path = "staticfiles/images/signature.png"  # <-- Update to your actual path
            canvas.drawImage(signature_path, logo_x, doctor_text_y + 10, width=80, height=25, mask='auto')
        except:
            pass
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

        # ---- Website Text ----
        footer_text = "www.pmxhealth.com"
        canvas.setFont(FONT_INTER_REGULAR, 8)
        canvas.setFillColorRGB(0.4, 0.4, 0.4)
        text_x = logo_x + logo_width + text_padding
        text_y = logo_y + 5
        canvas.drawString(text_x, text_y, footer_text)
    
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
            bottomMargin=90
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



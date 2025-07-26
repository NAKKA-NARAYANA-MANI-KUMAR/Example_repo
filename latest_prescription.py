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
    KeepTogether,
    Frame,
    BaseDocTemplate,
    PageTemplate,
    Indenter,
    PageBreak
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from reportlab.graphics.shapes import Drawing,Circle, String
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
PMX_TABLE_ALTERNATE_ROW = colors.HexColor("#F9FAFB")  # Alternating row color

# Font Configuration
FONT_FAMILY = "Inter"  # Base font family
FONT_INTER_LIGHT = "Inter-Light"  # Light weight
FONT_INTER_REGULAR = "Inter-Regular"  # Regular weight
FONT_INTER_BOLD = "Inter-Bold"  # Bold weight\
FONT_INTER_SEMIBOLD="Inter-SemiBold"
FONT_INTER_MEDIUM="Inter-Medium"
FONT_RALEWAY_MEDIUM="Raleway-Medium"
FONT_RALEWAY_SEMIBOLD="Raleway-SemiBold"
FONT_RALEWAY_REGULAR="Raleway"
# Typography Scale
FONT_SIZE_LARGE = 18  # Headers
FONT_SIZE_LARGE_MEDIUM = 16  # Headers
FONT_SIZE_MEDIUM = 12  # Subheaders
FONT_SIZE_SMALL = 10  # Supporting text
FONT_SIZE_BODY = 11  # Body text
FONT_SIZE_VERY_SMALL=8
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
print(A4[0],A4[1])
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
    TTFont(FONT_INTER_SEMIBOLD, "staticfiles/fonts/inter/Inter-SemiBold.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_RALEWAY_MEDIUM, "staticfiles/fonts/Raleway-Medium.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_RALEWAY_REGULAR, "staticfiles/fonts/Raleway-Regular.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_RALEWAY_SEMIBOLD, "staticfiles/fonts/Raleway-SemiBold.ttf")
)

metric = {
    "syrup": {"width": 15, "height": 14.09},
    "capsule": {"width": 15, "height": 15},
    "powder": {"width": 15, "height": 11.3},
    "tablet": {"width": 15, "height": 15.03}
}

class RoundedBox(Flowable):
    def __init__(self, width, height=None, content=None, corner_radius=8,border_radius=0.4,stroke_color=PMX_GREEN,fill_color=colors.white ):
        super().__init__()
        self.width = width
        self.height = height  
        self.content = content
        self.corner_radius = corner_radius
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.border_radius=border_radius

    def wrap(self, availWidth, availHeight):
        if self.content:
            content_width, content_height = self.content.wrap(availWidth, availHeight)
        else:
            content_width, content_height = 0, 0

        # If no fixed height is given, use content height
        self.width = self.width or content_width
        self.height = self.height or content_height

        return self.width, self.height

    def draw(self):
        self.canv.saveState()

        # Draw background box
        self.canv.setFillColor(self.fill_color)
        self.canv.setStrokeColor(self.stroke_color)
        self.canv.setLineWidth(self.border_radius)
        self.canv.roundRect(0, 0, self.width, self.height, self.corner_radius, fill=1, stroke=1)

        # Draw the content inside the box (0,0 origin)
        if self.content:
            self.content.wrapOn(self.canv, self.width, self.height)
            self.content.drawOn(self.canv, 0, 0)

        self.canv.restoreState()

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
        c.translate(self.left_margin-78, 0)

        # Draw the line slightly above the flowable base to avoid clipping
        y = self.thickness + 0.5  # Draw at 1.5 pts above the flowable's bottom

        c.setStrokeColor(PMX_TABLE_HEADER_BORDER)
        c.setLineWidth(self.thickness)
        c.line(0, y, self.page_width, y)

        c.restoreState()

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

    def _get_logo(self,width=60, height=60):
        """Load and return the clinic logo as an SVG image flowable.

        Returns:
            PrescriptionOnlySVGImage: Logo image sized appropriately for the header
        """
        # Try multiple possible paths for the logo
        possible_paths = [
            str(self.base_path / "pmx_green_logo.svg"),
            # str(
            #     Path(__file__).parent.parent.parent.parent.parent
            #     / "static"
            #     / "reports"
            #     / "pmx_green_logo.svg"
            # ),
            # str(
            #     Path(__file__).parent.parent.parent.parent.parent
            #     / "staticfiles"
            #     / "reports"
            #     / "pmx_green_logo.svg"
            # ),
            # str(
            #     Path(__file__).parent.parent.parent.parent.parent
            #     / "static"
            #     / "icons"
            #     / "pmx_green_logo.svg"
            # ),
            str(
                Path(__file__).parent.parent.parent.parent.parent
                / "staticfiles"
                / "icons"
                / "pmx_green_logo.svg"
            ),
            # "staticfiles/reports/pmx_green_logo.svg",
            # "static/reports/pmx_green_logo.svg",
            "staticfiles/icons/pmx_green_logo.svg",
            "static/icons/pmx_green_logo.svg",
        ]

        for logo_path in possible_paths:
            try:
                if os.path.exists(logo_path):
                    # Try to load SVG
                    svg = svg2rlg(logo_path)
                    if svg is not None:
                        return PrescriptionOnlySVGImage(logo_path, width, height)
                    # If SVG loading failed, try to load as regular image
                    return Image(logo_path, width, height)
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
            "CustomBoldStyle",
            fontName=FONT_INTER_BOLD,       # You need to register this font manually if not built-in
            fontSize=FONT_SIZE_MEDIUM,
            leading=14,                  # Line height
            textColor=PMX_GREEN,
            spaceAfter=0,                # Optional: spacing after paragraph
            spaceBefore=0,
        )
        credentials_style = ParagraphStyle(
            name="InterRegularStyle",
            fontName=FONT_INTER_REGULAR,     # Make sure this is registered (TTF)
            fontSize=FONT_SIZE_MEDIUM,                  # Matches font-size: 12px
            leading=14,                   # Matches line-height: 14px
            textColor=PMX_GREEN,
            spaceAfter=0,                 # No extra spacing (CSS doesn't include margin)
            spaceBefore=0,
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
            name="InterRightAligned",
            fontName=FONT_INTER_REGULAR,       # You need to register Inter-Regular.ttf
            fontSize=FONT_SIZE_SMALL,                    # Matches font-size: 10px
            leading=14,                     # Matches line-height: 14px
            textColor=PMX_GREEN,
            alignment=TA_RIGHT,            # Right-aligned text
            spaceBefore=0,
            spaceAfter=0,
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
        logo = self._get_logo(width=81, height=35.7)
        doctor_info = self._get_doctor_info(data)
        address = self._get_address(data)

        # Arrange in a single-row table with three columns
        table_data = [[Spacer(1,5.3),logo,Spacer(1,16), doctor_info, address]]
        table = Table(table_data, colWidths=[5.3,81,16,228, 190])
        table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING",(0, 0),(-1, -1),0,),  
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        total_table=Table([[table]],colWidths=[515])
        total_table.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1),0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 40),
                    ("TOPPADDING",(0, 0),(-1, -1),16),  
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                ]
            )
        )
        elements.append(total_table)
        #elements.append(Spacer(1, 10))
        
        elements.append(
            FullPageWidthHRFlowable(
                page_width=A4[0],        
                left_margin=72,          
                thickness=0.5,
                color=PMX_GREEN,
                spaceAfter=10
            )
        )
        return elements

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self._saved_pages = []
        super().__init__(*args, **kwargs)

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_pages)
        for page_num, page in enumerate(self._saved_pages, start=1):
            self.__dict__.update(page)
            self._template.total_pages = total_pages  # set total pages for footer
            self._template._add_logo_to_bottom_left(self, self._doc)
            super().showPage()
        super().save()

class RoundedPill(Flowable):
    def __init__(
        self,
        text,
        bg_color,
        radius=None,
        width=64,
        height=18,
        font_size=8,
        text_color=colors.white,
        border_color=None,
        border_width=0.2,
        font_name=FONT_INTER_REGULAR,
        icon_path=None,
        icon_width=0,
        icon_height=0,
        icon_text_padding=4,
        left_padding=4,
    ):
        super().__init__()
        self.text = str(text)
        self.bg_color = bg_color
        self.radius = radius if radius is not None else height / 2
        self.width = width
        self.height = height
        self.font_size = font_size
        self.text_color = text_color
        self.border_color = border_color
        self.border_width = border_width
        self.font_name = font_name

        # Icon handling
        self.icon_path = icon_path
        self.icon_width = icon_width
        self.icon_height = icon_height
        self.icon_text_padding = icon_text_padding
        self.left_padding = left_padding

        self.icon_drawing = None
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                drawing = svg2rlg(self.icon_path)
                scale_x = self.icon_width / drawing.width
                scale_y = self.icon_height / drawing.height
                drawing.scale(scale_x, scale_y)
                self.icon_drawing = drawing
            except Exception:
                self.icon_drawing = None

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.canv.saveState()

        # Draw pill background
        radius = min(self.radius, self.height / 2, self.width / 2)
        self.canv.setFillColor(self.bg_color)
        if self.border_color:
            self.canv.setStrokeColor(self.border_color)
            self.canv.setLineWidth(self.border_width)
            stroke_val = 1
        else:
            self.canv.setStrokeColor(self.bg_color)
            stroke_val = 0
        self.canv.roundRect(0, 0, self.width, self.height, radius, fill=1, stroke=stroke_val)

        # Set font and calculate text width
        self.canv.setFont(self.font_name, self.font_size)
        text_width = self.canv.stringWidth(self.text, self.font_name, self.font_size)

        # Total content width (icon + padding + text)
        content_width = text_width
        if self.icon_drawing:
            content_width += self.icon_width + self.icon_text_padding

        # Horizontal center position
        start_x = (self.width - content_width) / 2

        # Vertical center position
        center_y = self.height / 2

        # Draw icon if available
        if self.icon_drawing:
            icon_y = center_y - self.icon_height / 2
            renderPDF.draw(
                self.icon_drawing,
                self.canv,
                start_x,
                icon_y,
            )
            start_x += self.icon_width + self.icon_text_padding  # Shift X for text

        # Draw text centered vertically
        text_y = center_y - self.font_size / 4  # visually adjusted
        self.canv.setFillColor(self.text_color)
        self.canv.drawString(start_x, text_y, self.text)

        self.canv.restoreState()

# ------------------ Subclass with Content ------------------

class DoctorSignature(Flowable):
    def __init__(self, styles):
        super().__init__()
        self.styles = styles
        self.width = 0
        self.height = 60  # Adjust height if needed

    def draw(self):
        canvas = self.canv
        left_margin = 32
        base_y = 0  # relative to flowable position

        canvas.setFont(FONT_INTER_MEDIUM, 8)
        canvas.setFillColor(colors.black)
        canvas.drawString(left_margin, base_y + 33, "Dr. Samatha Tulla (MBBS, MD Internal Medicine)")

        canvas.setFont(FONT_INTER_LIGHT, 8)
        canvas.drawString(left_margin, base_y + 21, "Reg no: 68976 Telangana State Medical Council")

        try:
            signature_svg = "staticfiles/icons/dr_samatha_sign.svg"
            drawing = svg2rlg(signature_svg)

            target_width = 77
            target_height = 21.12
            scale_x = target_width / drawing.width
            scale_y = target_height / drawing.height
            drawing.scale(scale_x, scale_y)
            renderPDF.draw(drawing, canvas, x=left_margin, y=base_y)
        except Exception as e:
            print(f"SVG load failed: {e}")

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
        ),
        self.styles.add(
            ParagraphStyle(
                "Medicationss",
                fontName=FONT_INTER_SEMIBOLD,   # You must register this font if custom
                fontSize=FONT_SIZE_VERY_SMALL,
                leading=10,  # Matches line-height: 10px
                textColor=PMX_GREEN,
                alignment=TA_LEFT,
                underlineWidth=0.5,  # Optional: controls underline thickness
                spaceBefore=0,
                spaceAfter=0,
            )
        )
        self.styles.add(ParagraphStyle(
            "PatientName",
            fontName=FONT_RALEWAY_MEDIUM,       # Must be registered manually
            fontSize=18,                     # Matches font-size: 18px
            leading=21.784,                  # Matches line-height: 21.784px
            textColor=PMX_GREEN,
            spaceBefore=0,
            spaceAfter=0,
        ))
        # Date style
        self.styles.add(ParagraphStyle(
            "DateStyle",
            fontName=FONT_INTER_REGULAR,          # You need to register this if it's a TTF
            fontSize=FONT_SIZE_MEDIUM,                       # Matches font-size: 12px
            leading=21.784,                    # Matches line-height: 21.784px
            textColor=PMX_GREEN,
            spaceBefore=0,
            spaceAfter=0,
        ))
        
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
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=0,
                wordWrap="CJK",
            )
        )
        
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
                #wordWrap=None,
                keepWithNext=True,
                allowOrphans=0,
                #wordWrap="LTR",  # Use LTR to prevent character splitting
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
        
        self.styles.add(ParagraphStyle(
            "BoxInsideData",
            fontName=FONT_INTER_REGULAR,  # Ensure 'Inter' is registered; use 'Helvetica' if fallback needed
            fontSize=12,
            leading=18,  # Line height
            textColor=PMX_GREEN,
        ))
        self.styles.add(ParagraphStyle(
            "SvgBulletTitle",
            fontName=FONT_INTER_MEDIUM,               # Make sure Inter is registered
            fontSize=16,
            leading=24,                     # 150% line height
            textColor=PMX_GREEN,
        ))
        self.styles.add(ParagraphStyle(
            "bullet_after_text",
            fontName=FONT_INTER_REGULAR,                   # Make sure Inter-Regular is registered
            fontSize=12,
            leading=18,                         # Equivalent to line-height: 18px
            textColor=colors.HexColor("#003632"),     # Brand-800
            spaceBefore=0,
            spaceAfter=0,
            leftIndent=6
        ))

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
            ("FONTNAME", (0, 0), (-1, 0), FONT_RALEWAY_SEMIBOLD),
            ("FONTSIZE", (0, 0), (-1, 0), FONT_SIZE_SMALL),
            ("BOTTOMPADDING", (0, 0), (-1, 0), TABLE_ROW_PADDING),
            ("TOPPADDING", (0, 0), (-1, 0), TABLE_ROW_PADDING),
            ("LEFTPADDING", (0, 0), (-1, 0), TABLE_ROW_PADDING),
            ("RIGHTPADDING", (0, 0), (-1, 0), TABLE_ROW_PADDING),
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
            ("TOPPADDING", (0, 1), (-1, -1), TABLE_ROW_PADDING),
            ("BOTTOMPADDING", (0, 1), (-1, -1), TABLE_ROW_PADDING),
            ("LEFTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            ("RIGHTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            
            # Grid and Borders
            ("GRID", (0, 0), (-1, -1), 0.2, PMX_TABLE_GRID),
            ("LINEBELOW", (0, 0), (-1, 0), 0.2, PMX_GREEN),
            ("LINEAFTER", (0, 0), (0, -1), 0.2, PMX_GREEN),
            ("LINEAFTER", (1, 0), (1, -1), 0.2, PMX_GREEN),
            ("LINEAFTER", (2, 0), (2, -1), 0.2, PMX_GREEN),
            ("LINEAFTER", (3, 0), (3, -1), 0.2, PMX_GREEN),
            ("LINEAFTER", (4, 0), (4, -1), 0.2, PMX_GREEN),
            # Rounded Corners
            ("ROUNDEDCORNERS", [16, 16, 16, 16]),
            ("BOX", (0, 0), (-1, -1), 0.2, PMX_GREEN, None, None, "round"),
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
            combined_text = f"{name} <font size=12>{age} , {gender}</font>"
        elif age:
            combined_text = f"{name} <font size=12>{age} </font>"
        elif gender:
            combined_text = f"{name} <font size=12>{gender}</font>"
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
            name_date_data, colWidths=[415, 110]
        )
        name_date_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("VALIGN", (0, 0), (0, 0), "TOP"),
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        total_name_date_table = Table(
            [[name_date_data]], colWidths=[A4[0]-68]
        )
        total_name_date_table.setStyle(
            TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 34),
                ("RIGHTPADDING", (0, 0), (-1, -1), 34),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ])
        )
        elements.append(name_date_table)
        elements.append(Spacer(1, 16))
        return elements

    def svg_icon(self, path, width=12, height=12):
        try:
            drawing = svg2rlg(path)
            if drawing is None:
                raise FileNotFoundError(f"SVG file '{path}' could not be loaded or is invalid.")
        except Exception as e:
            print(f"Error loading SVG: {e}")
            # Return a blank box or a placeholder
            drawing = Drawing(width, height)
        
        original_width = drawing.width or 1
        original_height = drawing.height or 1
        drawing.scale(width / original_width, height / original_height)
        drawing.width = width
        drawing.height = height
        return drawing
    
    def _get_forms_(self, data: dict) -> Table:

        forms = data.get("forms", [])
        forms_starting = data.get("forms_starting", "")

        if not forms:
            return Spacer(1, 0)

        row = []
        col_widths = []

        if forms_starting:
            intro_para = Paragraph(forms_starting,ParagraphStyle(
                "frequency_duration",  # Custom left-aligned
                parent=self.styles["TableCell"],
                fontSize=FONT_SIZE_SMALL,
            ))
            intro_width= stringWidth(forms_starting, FONT_INTER_REGULAR , FONT_SIZE_SMALL)
            row.append(intro_para)
            col_widths.append(intro_width)

            row.append(Spacer(8, 0))
            col_widths.append(8)

        for idx, item in enumerate(forms):
            item_lower = item.lower()
            icon_path = os.path.join("staticfiles", "icons", f"{item_lower}.svg")

            if item_lower not in metric:
                continue

            icon = self.svg_icon(
                icon_path,
                width=metric[item_lower]["width"],
                height=metric[item_lower]["height"]
            )

            para = Paragraph(item, self.styles["TableCell"])
            para_width = stringWidth(item, FONT_INTER_REGULAR , FONT_SIZE_VERY_SMALL)

            row.append(icon)
            col_widths.append(icon.width)

            row.append(Spacer(4, 0))  # 4pt between icon and text
            col_widths.append(4)

            row.append(para)
            col_widths.append(para_width)

            if idx < len(forms) - 1:
                row.append(Spacer(8, 0))  # 8pt between icon–text pairs
                col_widths.append(8)

        forms_table_inner = Table([row], colWidths=col_widths, hAlign="RIGHT")
        forms_table_inner.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        forms_table = Table([[forms_table_inner]], colWidths=[A4[0] - 64])
        forms_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return forms_table

    def build_prescription_tables_per_page(self, full_table_data, col_widths, rows_per_chunk=7):
        """Split table into chunks per page and always apply rounded-corner style."""
        header = full_table_data[0]
        body = full_table_data[1:]

        tables = []
        for i in range(0, len(body), rows_per_chunk):
            chunk_rows = body[i:i + rows_per_chunk]
            chunk_data = [header] + chunk_rows

            # Every chunk gets full rounded corners
            table = self._build_styled_table(chunk_data, col_widths)
            tables.append(table)

        return tables

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
            for h in ["", "Medications", "Frequency", "Duration", "Remarks"]
        ]
        table_data = [headers]

        for i, med in enumerate(medications, 1):
            name = med.get("name", "").upper()
            external_url = med.get("external_url","")
            if external_url:
                name_ = Paragraph(f'<link href="{external_url}"><u>{name}</u></link>',self.styles["Medicationss"])
            else:
                name_ = Paragraph(f'{name}',self.styles["Medicationss"])
            strength = med.get("strength", "")
            form=med.get("form","")
            active_ingredients = med.get("active_ingredients", "")
            supplement_flowables = []
            # Supplement name with strength or type below (like Mixed, 500 mg)
            if strength and form and name:
                icon_path = os.path.join("staticfiles", "icons", f"{form.lower()}.svg")
                icon=self.svg_icon(
                    icon_path,
                    width=metric[form.lower()]["width"],
                    height=metric[form.lower()]["height"]
                )
                font_size = 8
                padding_top = 4
                padding_bottom = 4
                button_height = font_size + padding_top + padding_bottom
                # Calculate text width
                text_width = stringWidth(strength, FONT_INTER_REGULAR, 8)

                padding_left = 8
                padding_right = 8
                button_width = text_width + padding_left + padding_right
                pill = RoundedPill(
                    text=strength,
                    bg_color=colors.HexColor("#E6F4F3"),
                    radius=46.622,
                    width=button_width,
                    height=button_height,
                    font_size=8,
                    text_color=colors.HexColor("#003632"),
                    border_color=PMX_GREEN,
                    border_width=0.2,
                    font_name=FONT_INTER_REGULAR,
                )
                content_table = Table(
                    [
                        [icon,"", name_],
                        ["","",pill]
                    ],
                    colWidths=[15,10, 136]  # You can tweak 15 and 136 as needed
                )

                content_table.setStyle(
                    TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (2, -1), (2, -1), 4)
                    ])
                )

                supplement_flowables.append(content_table)

                
            supplement_cell = supplement_flowables if supplement_flowables else Paragraph("-", self.styles["TableCell"])


            dosage = med.get("dosage", "")
            dose_cell = Paragraph(dosage, self.styles["TableCell"])

            frequency_raw = med.get("frequency", "")
            timing = med.get("timing", "")

            def format_frequency_with_gray_dots(frequency: str) -> str:
                parts = frequency.strip().split("-")
                # Insert gray dot between values
                return ' <font color="#D9D9D9" size=10>•</font> '.join(parts)
            
            if timing:
                combined_text = f"{format_frequency_with_gray_dots(frequency_raw)}<br/><font color='#667085'>{timing}</font>"
                frequency_cell = Paragraph(combined_text, self.styles["TableCell"])
            else:
                frequency_cell = Paragraph(format_frequency_with_gray_dots(frequency_raw), self.styles["TableCell"])


            duration_cell = Paragraph(med.get("duration", ""), self.styles["TableCell"])

            instructions = med.get("instructions", "")
            available_in_clinic = med.get("available_in_clinic", False)
            
            remarks_flowables = []
            if instructions:
                remarks_flowables.append(
                    Paragraph(instructions, self.styles["TableCell"])
                )

            remarks_cell = remarks_flowables if remarks_flowables else Paragraph("", self.styles["TableCell"])

            row = [
                Paragraph(f'<nobr><font size="7">{str(i).zfill(2)}</font></nobr>', self.styles["RowNumber"]),
                supplement_cell,
                frequency_cell,
                duration_cell,
                remarks_cell,
            ]

            table_data.append(row)

        # Set 6 column widths matching the layout in the screenshot
        col_widths = [25,181,70,70,185]
        #col_widths = [25,161,50,50,160]

        return self._build_styled_table(table_data, col_widths)

    def _create_supplements_table(self, supplements: list) -> Table:
        """
        Builds the prescription table styled as per the provided screenshot.
        Only 6 columns: Number, Supplements, Dose, Frequency, Duration, Remarks.
        """

        # Header row
        headers = [
            Paragraph(h, self.styles["TableHeader"])
            for h in ["", "Supplements","Start on", "Frequency", "Duration", "Remarks"]
        ]
        table_data = [headers]

        for i, med in enumerate(supplements, 1):
            name = med.get("name", "").upper()
            external_url = med.get("external_url","")
            if external_url:
                name_ = Paragraph(f'<link href="{external_url}"><u>{name}</u></link>',self.styles["Medicationss"])
            else:
                name_ = Paragraph(f'{name}',self.styles["Medicationss"])
            strength = med.get("strength", "")
            form=med.get("form","")
            active_ingredients = med.get("active_ingredients", "")
            supplement_flowables = []
            # Supplement name with strength or type below (like Mixed, 500 mg)
            if strength and form and name:
                icon_path = os.path.join("staticfiles", "icons", f"{form.lower()}.svg")
                icon=self.svg_icon(
                    icon_path,
                    width=metric[form.lower()]["width"],
                    height=metric[form.lower()]["height"]
                )
                font_size = 8
                padding_top = 4
                padding_bottom = 4
                button_height = font_size + padding_top + padding_bottom
                # Calculate text width
                text_width = stringWidth(strength, FONT_INTER_REGULAR, 8)

                padding_left = 8
                padding_right = 8
                button_width = text_width + padding_left + padding_right
                pill = RoundedPill(
                    text=strength,
                    bg_color=colors.HexColor("#E6F4F3"),
                    radius=46.622,
                    width=button_width,
                    height=button_height,
                    font_size=8,
                    text_color=colors.HexColor("#003632"),
                    border_color=PMX_GREEN,
                    border_width=0.2,
                    font_name=FONT_INTER_REGULAR,
                )
                content_table = Table(
                    [
                        [icon,"", name_],
                        ["","",pill]
                    ],
                    colWidths=[15,10, 136]  # You can tweak 15 and 136 as needed
                )

                content_table.setStyle(
                    TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (2, -1), (2, -1), 4)
                    ])
                )

                supplement_flowables.append(content_table)

                
            supplement_cell = supplement_flowables if supplement_flowables else Paragraph("-", self.styles["TableCell"])

            start_from=med.get("start_from", "")
            start_from_cell = Paragraph(start_from, self.styles["TableCell"])

            frequency_raw = med.get("frequency", "")
            timing = med.get("timing", "")

            def format_frequency_with_gray_dots(frequency: str) -> str:
                parts = frequency.strip().split("-")
                # Insert gray dot between values
                return ' <font color="#D9D9D9" size=10>•</font> '.join(parts)
            
            if timing:
                combined_text = f"{format_frequency_with_gray_dots(frequency_raw)}<br/><font color='#667085'>{timing}</font>"
                frequency_cell = Paragraph(combined_text, self.styles["TableCell"])
            else:
                frequency_cell = Paragraph(format_frequency_with_gray_dots(frequency_raw), self.styles["TableCell"])


            duration_cell = Paragraph(med.get("duration", ""), self.styles["TableCell"])

            instructions = med.get("instructions", "")
            available_in_clinic = med.get("available_in_clinic", False)
            
            remarks_flowables = []
            if instructions:
                remarks_flowables.append(
                    Paragraph(instructions, self.styles["TableCell"])
                )

            remarks_cell = remarks_flowables if remarks_flowables else Paragraph("", self.styles["TableCell"])

            row = [
                Paragraph(f'<nobr><font size="7">{str(i).zfill(2)}</font></nobr>', self.styles["RowNumber"]),
                supplement_cell,
                start_from_cell,
                frequency_cell,
                duration_cell,
                remarks_cell,
            ]

            table_data.append(row)

        # Set 6 column widths matching the layout in the screenshot
        col_widths = [25,181,60,70,60,135]
        

        return self._build_styled_table(table_data, col_widths)
    
    def get_circular_icon_flowable(self,bg_color="#E7F5F3",text_color="#00625B",border_color="#00625B",text="P",radius=6.9,font_size=6.5) -> Drawing:

        size = radius * 2  
        d = Drawing(size, size)

        # Background circle
        circle = Circle(radius, radius, radius)
        circle.fillColor = colors.HexColor(bg_color)
        circle.strokeColor = colors.HexColor(border_color)
        circle.strokeWidth = 0.2
        d.add(circle)

        # Centered text
        text_obj = String(radius, radius - font_size * 0.3, text,
                        fontName=FONT_INTER_REGULAR,
                        fontSize=font_size,
                        fillColor=colors.HexColor(text_color),
                        textAnchor="middle")
        d.add(text_obj)

        return d

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

        
        headers = [
            Paragraph("", self.styles["TableHeader"]),  # First column (number)
            Paragraph("Therapy", self.styles["TableHeader"]),
            Paragraph("Start From", ParagraphStyle(
                "Start From",  
                parent=self.styles["TableHeader"],
                alignment=TA_CENTER
            )),
            Paragraph("Frequency & Duration", ParagraphStyle(
                "Frequency & Duration",  
                parent=self.styles["TableHeader"],
                alignment=TA_CENTER
            )),
            Paragraph("Remarks", self.styles["TableHeader"]),
        ]
        table_data = [headers]

        for i, therapy in enumerate(therapies, 1):
            name=therapy.get("name", "")
            start_from_cell=Paragraph(therapy.get("start_from", ""), self.styles["TableCell"]),
            frequency=therapy.get("frequency", "")
            session_days=therapy.get("session_days", "")
            session_time=Paragraph(therapy.get("session_time", ""), ParagraphStyle(
                "frequency_duration",  # Custom left-aligned
                parent=self.styles["TableCell"],
                textColor=colors.HexColor("#667085")
            )),
            duration=therapy.get("duration", "")
        
            frequency_duration=Paragraph(f"{frequency} |{duration}",ParagraphStyle(
                "frequency_duration",  # Custom left-aligned
                parent=self.styles["TableCell"],
                textColor=colors.HexColor("#667085")
            ))
            remarks_cell=Paragraph(therapy.get("remarks", ""), self.styles["TableCell"]),
            
            if name:
                name_=name.replace(" ","_")
                icon_path = os.path.join("staticfiles", "icons", f"{name_.lower()}.svg")
                icon=self.svg_icon(
                    icon_path,
                    width=27,
                    height=18
                )
                name_para=Paragraph(therapy.get("name", ""), self.styles["Medicationss"]),
                content_table = Table(
                    [
                        [icon,"", name_para],
                    ],
                    colWidths=[27,10, 124]  # You can tweak 15 and 136 as needed
                )

                content_table.setStyle(
                    TableStyle([
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ])
                )

            days_list = []
            days_dict = {"Mon": "M", "Tue": "T", "Wed": "W", "Thu": "Th", "Fri": "F", "Sat": "S", "Sun": "Su"}

            for index, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                if day in session_days:
                    icon = self.get_circular_icon_flowable(
                        text=days_dict[day],
                        bg_color="#80C6C0",
                        text_color="#FFFFFF",
                        border_color="#00625B"
                    )
                else:
                    icon = self.get_circular_icon_flowable(
                        text=days_dict[day],
                        bg_color="#E7F5F3",
                        text_color="#00625B",
                        border_color="#00625B"
                    )

                days_list.append(icon)

                # Add 5pt horizontal spacer between each icon, except after the last one
                if index < 6:
                    days_list.append(Spacer(width=5, height=0))

            # Create the table with a single row
            days_table = Table(
                [days_list],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER")
                ]
            )
            frequency_duration_table = Table(
                [[days_table],
                [session_time],
                [frequency_duration]],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER")
                ]
            )

            row = [
                Paragraph(f'<nobr><font size="7">{str(i).zfill(2)}</font></nobr>', self.styles["RowNumber"]),
                content_table,
                start_from_cell,
                frequency_duration_table,
                remarks_cell,
            ]

            table_data.append(row)
        col_widths = [25,181,80,140,105]
        return self._build_styled_table(table_data, col_widths)

    def create_diagnosis_pill_table(self, diagnoses: list,title) -> Table:
        bullets = []
        icon_path = os.path.join("staticfiles","icons","bullet_text_icon.svg")  
        icon_ = self.svg_icon(icon_path, width=24, height=24)
        title_para = Paragraph(title, self.styles["SvgBulletTitle"])

        header=Table([[
            icon_,
            Spacer(1,10),
            title_para
        ]],colWidths=[24,10,None])
        header.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        bullets.append([header])
        bullets.append([Spacer(1,8)])
        icon_path = os.path.join("staticfiles","icons","bullet.svg")  
        icon_bullet = self.svg_icon(icon_path, width=16, height=16)
        for i, item in enumerate(diagnoses):
            bullets.append([Paragraph(f"• {item}", self.styles["bullet_after_text"])])

        if bullets:
            bullet_table = Table(bullets,colWidths=[A4[0]-64])
            
            bullet_table.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, 0), 16),
                ("BOTTOMPADDING", (0,-1), (-1, -1), 16),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ROUNDEDCORNERS", [16, 16, 16, 16]),
                ("BOX", (0, 0), (-1, -1), 0.2, PMX_GREEN, None, None, "round"),
            ]))


            return bullet_table
        return None

    def _create_other_sections(self, data: dict,sections_to_process) -> list:
        """Create additional sections of the prescription excluding diagnoses."""
        elements = []


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

                if custom_handler:
                    # Use custom handler for special sections like therapies
                    table = custom_handler(section_data)
                    if table:
                        elements.append(table)
                else:
                    elements.append(KeepTogether(self.create_diagnosis_pill_table(section_data,title)))
                elements.append(Spacer(1, 16))

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

        story = []        
        
        sections_to_process = [
            ("symptoms", "Current Symptoms", None),
            ("signs", "Clinical Signs", None),
            ("diagnoses", "Diagnosis", None)
        ]
        other_sections = self._create_other_sections(data,sections_to_process)
        story.append(Indenter(left=32, right=32))
        story.extend(other_sections)
        story.append(Indenter(left=-32, right=-32))
        story.append(PageBreak())
        story.append(self._get_forms_(data))
        story.append(Spacer(1, 16))
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
                        "frequency": med.get("frequency", ""),
                        "duration": med.get("duration", ""),
                        "instructions": med.get("instructions", ""),
                        "timing": med.get("timing", ""),
                        "available_in_clinic": med.get("available_in_clinic", ""),
                        "external_url": med.get("external_url", ""),
                    }
                )

        if medications:
            story.append(KeepTogether(self._create_prescription_table(medications)))
            story.append(Spacer(1, 16))
        
        if "supplements" in data:
            # Direct access
            supplements = data.get("supplements", [])
        elif "consultation" in data and "reference_data" in data.get(
            "consultation", {}
        ):
            # From consultation reference_data
            ref_supplements = (
                data.get("consultation", {})
                .get("reference_data", {})
                .get("supplements", [])
            )
            for med in ref_supplements:
                supplements.append(
                    {
                        "name": med.get("name", ""),
                        "strength": med.get("strength", ""),
                        "frequency": med.get("frequency", ""),
                        "duration": med.get("duration", ""),
                        "instructions": med.get("instructions", ""),
                        "start_from": med.get("start_from", ""),
                        "timing": med.get("timing", ""),
                        "available_in_clinic": med.get("available_in_clinic", ""),
                        "external_url": med.get("external_url", ""),
                    }
                )

        if supplements:
            story.append(KeepTogether(self._create_supplements_table(supplements)))
            story.append(Spacer(1, 16))
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
            story.append(self._create_therapies_table(therapies))
            story.append(Spacer(1, self.PAGE_MARGIN / 4))
            story.append(DoctorSignature(self.styles))
            story.append(PageBreak())  # <- Add signature here
            story.append(Spacer(1, self.PAGE_MARGIN / 4))

        

        sections_to_process = [
            ("additional_diagnoses","Additional Diagnostics",None),
            ("advices", "Advice", None)
        ]
        other_sections_ = self._create_other_sections(data,sections_to_process)
        story.extend(other_sections_)
        story.append(Paragraph("prescription ends here", self.styles["PrescriptionEnds"]))
        story.append(Spacer(1, self.PAGE_MARGIN / 4))

        return story

    def _add_logo_to_bottom_left(self, canvas, doc):
        logo_x = 26
        logo_y = 16
        text_padding = 370
        logo_width = 0

        # Draw PMX logo
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
            fallback_text = "PMX Health"
            canvas.setFont(FONT_INTER_BOLD, 10)
            canvas.setFillColor(PMX_GREEN)
            canvas.drawString(logo_x, logo_y, fallback_text)
            logo_width = canvas.stringWidth(fallback_text, FONT_INTER_BOLD, 10)

        # --- Page Number Format: Page 01 - 03 ---
        current_page = canvas.getPageNumber()
        total_pages = getattr(self, "total_pages", 0)
        page_text = f"Page {str(current_page).zfill(2)} - {str(total_pages).zfill(2)}"

        canvas.setFont(FONT_INTER_REGULAR, 8)
        canvas.setFillColorRGB(0.4, 0.4, 0.4)
        text_x = logo_x + logo_width + text_padding
        text_y = logo_y + 5
        canvas.drawString(text_x, text_y, page_text)

    def add_bottom_left_image(self, image_path,x,y, width=34.7, height=80) -> list:
        """
        Returns a list of flowables to place an image at the bottom-left corner of the page.

        Args:
            image_path (str): Path to the image file.
            width (float): Width of the image in points.
            height (float): Height of the image in points.

        Returns:
            list: A list containing a Flowable that renders the image at the bottom-left.
        """
        class BottomLeftImageFlowable(Flowable):
            def __init__(self, path, img_width, img_height):
                super().__init__()
                self.path = path
                self.img_width = img_width
                self.img_height = img_height
                self.x=x
                self.y=y

            def wrap(self, availWidth, availHeight):
                return 0, 0  # Doesn't consume space in normal flow

            def draw(self):
                try:
                    # Draw image at absolute bottom-left (0, 0)
                    self.canv.drawImage(
                        self.path,
                        x=self.x,
                        y=self.y,
                        width=self.img_width,
                        height=self.img_height,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                except Exception as e:
                    print(f"Error rendering bottom-left image: {e}")

        return [BottomLeftImageFlowable(image_path, width, height)]

# ------------------ Flask App ------------------
app = Flask(__name__)
@app.route("/generate_prescription", methods=["POST"])
def generate_prescription():
    data = request.get_json()
    buffer = io.BytesIO()

    template = PrescriptionPage()

    content_frame = Frame(
        x1=0,
        y1=169,
        width=A4[0],
        height=A4[1] - 169 - 134,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )

    def draw_every_page(canvas, doc):
        canvas.saveState()
        
        header_flowables = (
            template.add_bottom_left_image("x_logo.png",x=-6,y=-74)+
            template._create_header(data)
            + template._create_patient_info(data)
        )

        header_frame = Frame(
            x1=0,
            y1=A4[1] - 134,
            width=595,
            height=134,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        header_frame.addFromList(header_flowables, canvas)
        canvas.restoreState()

    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0,
        rightMargin=0,
        topMargin=0,
        bottomMargin=169,
    )
    doc.addPageTemplates([
        PageTemplate(id="PrescriptionPage", frames=[content_frame], onPage=draw_every_page)
    ])

    def canvasmaker(filename, **kwargs):
        c = NumberedCanvas(filename, **kwargs)
        c._template = template
        return c

    flowables = template.generate(data)
    doc.build(flowables, canvasmaker=canvasmaker)
    with open("output_from_buffer__.pdf", "wb") as f:
        f.write(buffer.getvalue())
        
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="prescription.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)



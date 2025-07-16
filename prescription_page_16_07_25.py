# Standard library imports
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle

# Third-party imports for SVG handling
from svglib.svglib import svg2rlg

# ------------------------------------------------------------------------------
# Logger configuration
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Visual Style Constants

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
    TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf")
)
pdfmetrics.registerFont(
    TTFont(FONT_INTER_BOLD, "staticfiles/fonts/inter/Inter-Bold.ttf")
)

# ------------------------------------------------------------------------------
# Base Classes and Flowables


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


# ------------------------------------------------------------------------------
# Template Classes


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
            fontSize=FONT_SIZE_SMALL,
            textColor=PMX_GREEN,
            leading=12,
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
        clinic_name = "PMX Health"
        clinic_address_lines = [
            "4th floor, Rd Number 44,",
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
            if clinic_info.get("name"):
                clinic_name = clinic_info.get("name", clinic_name)
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
            leading=12,
            alignment=TA_RIGHT,
        )

        # Build list of formatted paragraphs
        address = [Paragraph(clinic_name, address_style)]
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
        elements.append(Spacer(1, 1))
        elements.append(
            PrescriptionOnlyHRFlowable(
                width="100%", thickness=0.5, color=PMX_GREEN, spaceAfter=5
            )
        )
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


# ------------------------------------------------------------------------------
# Main Prescription Page


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
                fontSize=FONT_SIZE_LARGE_MEDIUM,
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
                textColor=colors.black,
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
                fontSize=FONT_SIZE_SMALL,
                textColor=colors.black,
                leading=12,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=0,
                wordWrap="CJK",
            )
        )
        # Row number style - prevents character splitting
        self.styles.add(
            ParagraphStyle(
                "RowNumber",
                fontName=FONT_INTER_REGULAR,
                fontSize=FONT_SIZE_SMALL,
                textColor=colors.black,
                leading=12,
                alignment=TA_CENTER,
                spaceBefore=0,
                spaceAfter=0,
                wordWrap="LTR",  # Use LTR to prevent character splitting
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
                borderWidth=1,
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
            combined_text = f"{name} <font size=9>({age} years, {gender})</font>"
        elif age:
            combined_text = f"{name} <font size=9>({age} years)</font>"
        elif gender:
            combined_text = f"{name} <font size=9>({gender})</font>"
        else:
            combined_text = name

        logger.info(f"Patient info text: {combined_text}")

        current_date = datetime.now().strftime("%d-%m-%Y")

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
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, 0), 10),  # Added 10 points padding
                    ("RIGHTPADDING", (0, 0), (0, 0), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), -15),
                ]
            )
        )
        elements.append(name_date_table)
        elements.append(Spacer(1, 5))
        return elements

    def _create_prescription_table(self, medications: list) -> Table:
        """Build the prescription table for medications.

        Args:
            medications (list): List of medication dictionaries with structure:
            [
                {
                    "name": "Medication Name",
                    "strength": "10mg",
                    "dosage": "1 tablet",
                    "frequency": "Twice daily",
                    "duration": "7 days",
                    "instructions": "Take after meals",
                    "start_from": "2023-01-01",
                    "timing": "Morning",
                    "available_in_clinic": True,
                    "external_url": "https://www.google.com"
                },
                ...
            ]

        Returns:
            Table: Styled table containing medication information
        """
        if not medications:
            return None

        headers = [
            Paragraph(h, self.styles["TableHeader"])
            for h in [
                "",
                "Medications",
                "Dosage",
                "Frequency",
                "Timing",
                "Duration",
                "Start From",
                "How to Buy",
                "Remarks",
            ]
        ]
        table_data = [headers]

        for i, med in enumerate(medications, 1):
            name = med.get("name", "")
            active_ingredients = med.get("active_ingredients", "")
            medication = (
                f"<i>{name}</i>\n<i><font size=7>({active_ingredients})</font></i>"
                if active_ingredients
                else f"<i>{name}</i>"
            )

            # Create dosage with strength below it
            dosage = med.get("dosage", "")
            strength = med.get("strength", "")
            dosage_strength = f"{dosage}\n{strength}" if strength else dosage
            timing = med.get("timing", "")
            # How to Buy column logic
            available_in_clinic = med.get("available_in_clinic", False)
            external_url = med.get("external_url", "")
            how_to_buy_cell = None
            if available_in_clinic:
                button = Paragraph("Available @ PMX", self.styles["PMXAvailableButton"])
                button_table = Table([[button]], colWidths=[80])
                button_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ]
                    )
                )
                how_to_buy_cell = button_table
            elif external_url:
                link_style = ParagraphStyle(
                    "LinkStyle",
                    parent=self.styles["TableCell"],
                    alignment=TA_CENTER,
                    textColor=colors.HexColor("#007bff"),
                    underline=True,
                )
                link_html = f'<link href="{external_url}">Link to buy</link>'
                how_to_buy_cell = Paragraph(link_html, link_style)
            else:
                how_to_buy_cell = Paragraph("", self.styles["TableCell"])

            # Remarks column: only instructions/notes
            instructions = med.get("instructions", "")
            remarks_cell = (
                Paragraph(
                    instructions,
                    ParagraphStyle(
                        "RemarksCell",
                        parent=self.styles["TableCell"],
                        alignment=TA_CENTER,
                    ),
                )
                if instructions
                else Paragraph("", self.styles["TableCell"])
            )

            row = [
                Paragraph(str(i), self.styles["RowNumber"]),
                Paragraph(medication, self.styles["TableCell"]),
                Paragraph(dosage_strength, self.styles["TableCell"]),
                Paragraph(med.get("frequency", ""), self.styles["TableCell"]),
                Paragraph(med.get("timing", ""), self.styles["TableCell"]),
                Paragraph(med.get("duration", ""), self.styles["TableCell"]),
                Paragraph(med.get("start_from", ""), self.styles["TableCell"]),
                how_to_buy_cell,
                remarks_cell,
            ]
            table_data.append(row)

        col_widths = [
            TABLE_COL_NUMBER
            * AVAILABLE_WIDTH
            * 1.5,  # Number column (increased by 50%)
            0.16 * AVAILABLE_WIDTH,  # Medications column (16%)
            0.10 * AVAILABLE_WIDTH,  # Dosage column (10%)
            0.11 * AVAILABLE_WIDTH,  # Frequency column (11%)
            0.10 * AVAILABLE_WIDTH,  # Timing column (10%)
            0.10 * AVAILABLE_WIDTH,  # Duration column (10%)
            0.08 * AVAILABLE_WIDTH,  # Start From column (8%)
            0.15 * AVAILABLE_WIDTH,  # How to Buy column (15%)
            0.20 * AVAILABLE_WIDTH,  # Remarks column (20%)
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

            # Standard bullet point list for diagnoses
            for item in diagnosis_data:
                if isinstance(item, dict) and "name" in item:
                    diagnosis_elements.append(
                        Paragraph(f"• {item['name']}", self.styles["PMXBodyText"])
                    )
                else:
                    diagnosis_elements.append(
                        Paragraph(f"• {item}", self.styles["PMXBodyText"])
                    )

            diagnosis_elements.append(Spacer(1, self.PAGE_MARGIN / 4))

        # Add diagnosis section first
        story.extend(diagnosis_elements)

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

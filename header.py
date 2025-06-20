# ----------------------------- Flask PDF Prescription Generator -----------------------------

# Standard library imports
from flask import Flask, request, send_file
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    Flowable,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
import io
import os
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

# Logger configuration
import logging
logger = logging.getLogger(__name__)

# ----------------------------- Constants -----------------------------
# Colors
PMX_GREEN = colors.HexColor("#00625B")
PMX_GREEN_LIGHT = colors.HexColor("#EFE8CE")
PMX_BUTTON_BG = colors.HexColor("#E6F4F3")
PMX_BACKGROUND = colors.HexColor("#F8F9FA")
PMX_TABLE_HEADER_BG = colors.HexColor("#f5f5f5")
PMX_TABLE_GRID = colors.HexColor("#e0e0e0")
PMX_TABLE_HEADER_BORDER = colors.HexColor("#d0d0d0")
PMX_TABLE_ALTERNATE_ROW = colors.HexColor("#F0F2F6")

# Fonts
FONT_FAMILY = "Inter"
FONT_INTER_LIGHT = "Inter-Light"
FONT_INTER_REGULAR = "Inter-Regular"
FONT_INTER_BOLD = "Inter-Bold"

# Font Sizes
FONT_SIZE_LARGE = 18
FONT_SIZE_LARGE_MEDIUM = 16
FONT_SIZE_MEDIUM = 12
FONT_SIZE_SMALL = 10
FONT_SIZE_BODY = 11

# Layout
PAGE_MARGIN = 0.3 * inch
TABLE_PADDING = 8
TABLE_ROW_PADDING = 10
TABLE_HEADER_PADDING = 12
AVAILABLE_WIDTH = (8.5 * inch) - (1.5 * inch)

# Defaults
DEFAULT_DOCTOR_NAME = "Dr. Samatha Tulla"
DEFAULT_SPECIALIZATION = "Internal Medicine Physician"
DEFAULT_ADDITIONAL_INFO = "& Diabetologist"
DEFAULT_REGISTRATION = "PMX-12345"

# Font Registration
pdfmetrics.registerFont(TTFont(FONT_INTER_LIGHT, "staticfiles/fonts/inter/Inter-Light.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_BOLD, "staticfiles/fonts/inter/Inter-Bold.ttf"))

# ----------------------------- Custom Flowables -----------------------------
class PrescriptionOnlyHRFlowable(Flowable):
    def __init__(self, width="100%", thickness=1, color=colors.black, spaceAfter=0):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.color = color
        self.spaceAfter = spaceAfter
        self.hAlign = "LEFT"

    def wrap(self, availWidth, availHeight):
        self.calcWidth = float(self.width[:-1]) * availWidth / 100.0 if isinstance(self.width, str) and self.width.endswith("%") else self.width
        return (self.calcWidth, self.thickness + self.spaceAfter)

    def draw(self):
        self.canv.setLineWidth(self.thickness)
        self.canv.setStrokeColor(self.color)
        self.canv.line(0, self.thickness, self.calcWidth, self.thickness)


class PrescriptionOnlySVGImage(Flowable):
    def __init__(self, svg_path, width=None, height=None):
        super().__init__()
        self.svg = svg2rlg(svg_path)
        self.svg_width = self.svg.width
        self.svg_height = self.svg.height
        if width:
            scale = width / self.svg_width
            self.width = width
            self.height = self.svg_height * scale
        elif height:
            scale = height / self.svg_height
            self.height = height
            self.width = self.svg_width * scale
        else:
            self.width = self.svg_width
            self.height = self.svg_height
        if width or height:
            self.svg.scale(self.width / self.svg_width, self.height / self.svg_height)

    def wrap(self, *args):
        return (self.width, self.height)

    def draw(self):
        renderPDF.draw(self.svg, self.canv, 0, 0)


# ----------------------------- Base Page -----------------------------
class PrescriptionOnlyPMXBasePage:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.base_path = Path(__file__).parent / "staticfiles" / "icons"

    def generate(self, content_elements):
        return list(content_elements)


# ----------------------------- Template -----------------------------
class PrescriptionOnlyTemplate(PrescriptionOnlyPMXBasePage):
    def __init__(self):
        super().__init__()
        self.pmx_green = PMX_GREEN
        self.pmx_green_light = PMX_GREEN_LIGHT

    def _get_logo(self):
        possible_paths = [
            str(self.base_path / "pmx_health.svg"),
            str(self.base_path / "pmx_health.png"),
            "staticfiles/icons/pmx_health.svg",
            "staticfiles/icons/pmx_health.png",
            "static/icons/pmx_health.svg",
            "static/icons/pmx_health.png",
        ]
        for logo_path in possible_paths:
            try:
                if os.path.exists(logo_path):
                    ext = os.path.splitext(logo_path)[1].lower()
                    if ext == ".svg":
                        svg = svg2rlg(logo_path)
                        if svg:
                            return PrescriptionOnlySVGImage(logo_path, width=60)
                    elif ext in [".png", ".jpg", ".jpeg"]:
                        return Image(logo_path, width=60, height=60)
            except Exception as e:
                print(f"Error loading logo from {logo_path}: {e}")
                continue
        return Paragraph(
            "PMX Health",
            ParagraphStyle("LogoPlaceholder", fontName=FONT_INTER_BOLD, fontSize=16, textColor=PMX_GREEN, alignment=TA_LEFT),
        )

    def _get_doctor_info(self, data):
        name_style = ParagraphStyle("DoctorName", fontName=FONT_INTER_BOLD, fontSize=FONT_SIZE_MEDIUM, textColor=PMX_GREEN, leading=14, alignment=TA_LEFT)
        credentials_style = ParagraphStyle("Credentials", fontName=FONT_INTER_LIGHT, fontSize=FONT_SIZE_SMALL, textColor=PMX_GREEN, leading=12, alignment=TA_LEFT)
        doctor_info = data.get("doctor") if data else None
        info = []
        if doctor_info:
            doctor_name = doctor_info.get("name", "")
            if doctor_name and not doctor_name.startswith("Dr."):
                doctor_name = f"Dr. {doctor_name}"
            if doctor_name:
                info.append(Paragraph(doctor_name, name_style))
            specialization = doctor_info.get("specialization")
            if specialization:
                info.append(Paragraph(specialization, credentials_style))
            registration = doctor_info.get("registration_number", doctor_info.get("registration"))
            registration_state = doctor_info.get("registration_state")
            if registration:
                reg_text = f"Reg No: {registration}"
                if registration_state:
                    reg_text += f" ({registration_state})"
                info.append(Paragraph(reg_text, credentials_style))
            elif registration_state:
                info.append(Paragraph(f"State: {registration_state}", credentials_style))
        if not info:
            info = [
                Paragraph(DEFAULT_DOCTOR_NAME, name_style),
                Paragraph(DEFAULT_SPECIALIZATION, credentials_style),
                Paragraph(DEFAULT_ADDITIONAL_INFO, credentials_style),
            ]
        return info

    def _get_address(self, data):
        clinic_name = "PMX Health"
        clinic_address_lines = [
            "4th floor, Rd Number 44,",
            "Jubilee Hills, Hyderabad,",
            "Telangana - 500033",
        ]
        use_data_doctor = data and data.get("source_data", {}).get("use_consultation_doctor", False)
        if use_data_doctor and "report_info" in data and "clinic" in data["report_info"]:
            clinic_info = data["report_info"]["clinic"]
            if clinic_info.get("name"):
                clinic_name = clinic_info["name"]
            if clinic_info.get("address"):
                address = clinic_info["address"]
                clinic_address_lines = address.split(", ") if ", " in address else address.split(",")
        address_style = ParagraphStyle("Address", fontName=FONT_INTER_LIGHT, fontSize=FONT_SIZE_SMALL, textColor=PMX_GREEN, leading=12, alignment=TA_RIGHT)
        address = [Paragraph(clinic_name, address_style)]
        for line in clinic_address_lines:
            address.append(Paragraph(line, address_style))
        return address

    def _create_header(self, data=None):
        elements = []
        logo = self._get_logo()
        doctor_info = self._get_doctor_info(data)
        address = self._get_address(data)
        table_data = [[logo, doctor_info, address]]
        table = Table(table_data, colWidths=[60, 260, 180])
        table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("ALIGN", (2, 0), (2, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, -1), -20),
            ("LEFTPADDING", (1, 0), (1, -1), 0),
            ("LEFTPADDING", (2, 0), (2, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), -40),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 1))
        elements.append(PrescriptionOnlyHRFlowable(width="100%", thickness=0.5, color=PMX_GREEN, spaceAfter=5))
        return elements

    def generate(self, data=None):
        story = []
        story.extend(self._create_header(data))
        # Add more content sections below as needed
        return story


# ----------------------------- Flask App -----------------------------
app = Flask(__name__)

@app.route("/generate-prescription", methods=["POST"])
def generate_prescription():
    data = request.get_json()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    template = PrescriptionOnlyTemplate()
    flowables = template.generate(data)
    doc.build(flowables)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="prescription.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)
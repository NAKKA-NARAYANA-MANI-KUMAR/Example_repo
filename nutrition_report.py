# === main.py ===

import os
import io
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from io import BytesIO

# ReportLab Core
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,KeepInFrame,
    Image, Flowable, KeepTogether, PageBreak, SimpleDocTemplate, ListItem, ListFlowable,Indenter,NextPageTemplate
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch, mm, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.shapes import Drawing,Rect, String, Line
from reportlab.lib.colors import Color,HexColor, white, black
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
from reportlab.graphics.shapes import Group
from reportlab.platypus import Image as RLImage

# SVG Rendering
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

# JSON Handling (optional if needed)
import json
svg_dir = "staticfiles/icons/"

# === Brand Colors ===
PMX_GREEN = colors.HexColor("#00625B")
PMX_GREEN_LIGHT = colors.HexColor("#EFE8CE")
PMX_BUTTON_BG = colors.HexColor("#E6F4F3")
PMX_TABLE_GRID = colors.HexColor("#e0e0e0")  # Table grid lines
PMX_TABLE_ALTERNATE_ROW = colors.HexColor("#F0F2F6")  # Alternating row color

# === Fonts ===
FONT_INTER_LIGHT = "Inter-Light"
FONT_INTER_REGULAR = "Inter-Regular"
FONT_INTER_BOLD = "Inter-Bold"
FONT_INTER_MEDIUM = "Inter-Medium"
FONT_INTER_SEMI_BOLD = "Inter-SemiBold"
FONT_RALEWAY_REGULAR = "Raleway-Regular"
FONT_RALEWAY_MEDIUM = "Raleway-Medium"
FONT_RALEWAY_BOLD = "Raleway-Bold"
FONT_RALEWAY_SEMI_BOLD= "Raleway-SemiBold"
FONT_RALEWAY_LIGHT = "Raleway-Light"

# === Register Fonts ===
pdfmetrics.registerFont(TTFont(FONT_INTER_LIGHT, "staticfiles/fonts/inter/Inter-Light.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_MEDIUM, "staticfiles/fonts/inter/Inter-Medium.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_BOLD, "staticfiles/fonts/inter/Inter-Bold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_SEMI_BOLD, "staticfiles/fonts/Inter-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_MEDIUM, "staticfiles/fonts/Raleway-Medium.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_REGULAR, "staticfiles/fonts/Raleway-Regular.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_BOLD, "staticfiles/fonts/Raleway-Bold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_SEMI_BOLD, "staticfiles/fonts/Raleway-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_LIGHT, "staticfiles/fonts/Raleway-Light.ttf"))

# === Font Sizes ===
FONT_SIZE_LARGE = 18
FONT_SIZE_LARGE_MEDIUM = 16
FONT_SIZE_MEDIUM = 12
FONT_SIZE_SMALL = 10
FONT_SIZE_BODY = 11

# === Layout Constants ===
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 0
RIGHT_MARGIN = 0
AVAILABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
HEADER_HEIGHT = 80
FOOTER_HEIGHT = 80
TABLE_COL_NUMBER = 0.05
TABLE_PADDING = 8
TABLE_HEADER_PADDING = 12

# === Base Classes ===

class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        self.allowSplitting = 0
        self.custom_toc_entries = []

        super().__init__(filename, **kwargs)

    def afterFlowable(self, flowable):
        # TOC disabled – do nothing
        return

                # self.custom_toc_entries.append((0, text, self.page+3))

class ThriveRoadmapOnlySVGImage:
    def __init__(self, filename, width=None, height=None):
        self.filename = filename
        self.width = width
        self.height = height

class FullPageWidthHRFlowable(Flowable):
    """
    Draws a horizontal line across the entire page width (ignoring margins).
    Works in any flowable frame by translating left, and drawing at safe Y-position.
    """

    def __init__(self, page_width=PAGE_WIDTH, left_margin=0, thickness=0.001, color=colors.HexColor("#80C6C0"), spaceAfter=0):
        super().__init__()
        self.page_width = page_width
        self.left_margin = left_margin
        self.thickness = thickness
        self.color = color
        self.spaceAfter = spaceAfter
        self.height = self.thickness + self.spaceAfter 

    def wrap(self, availWidth, availHeight):
        return (availWidth, self.height)

    def draw(self):
        c = self.canv
        c.saveState()

        c.translate(self.left_margin, 0)

        c.setStrokeColor(self.color)
        c.setLineWidth(self.thickness)
        c.line(0, self.thickness , self.page_width, self.thickness)

        c.restoreState()

class PDFStyleConfig:
    def __init__(self):

        # --- Colors ---
        self.WHITE = colors.white
        self.PMX_GREEN = PMX_GREEN
        self.PMX_GREEN_LIGHT = PMX_GREEN_LIGHT
        self.GLOW_COLOR = colors.Color(1, 1, 1, alpha=0.15)  # Simulated text-shadow rgba(255,255,255,0.92)

        # --- Font Sizes ---
        self.FONT_HUGE = 100
        self.FONT_LARGE = 18
        self.FONT_MEDIUM = 12
        self.FONT_SMALL = 10
        self.styles = getSampleStyleSheet()

        # --- Paragraph Styles (example) ---
        self.heading_style = ParagraphStyle(
            name="Heading",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=self.FONT_HUGE,
            textColor=self.WHITE,
            alignment=1,  # Centered
            spaceAfter=12
        )

    def draw_glow_text(self, canvas, text, x, y, font=FONT_INTER_SEMI_BOLD, size=100):
        """
        Simulates a text shadow/glow effect by drawing soft layers under the main text.
        """
        canvas.saveState()
        canvas.setFont(font, size)
        shadow_color = self.GLOW_COLOR
        offsets = [-1, 0, 1]

        for dx in offsets:
            for dy in offsets:
                if dx != 0 or dy != 0:
                    canvas.setFillColor(shadow_color)
                    canvas.drawString(x + dx, y + dy, text)

        canvas.setFillColor(self.WHITE)
        canvas.drawString(x, y, text)
        canvas.restoreState()

class ThrivePageRenderer:
    def __init__(self, template):
        self.template = template

    def draw_header(self, canvas, doc):
        canvas.saveState()
        # Draw left logo on every page (prefer PNG pattern over older SVG)
        logo_candidates = [
            os.path.join("staticfiles", "icons", "converted_pattern.png"),
            os.path.join("staticfiles", "icons", "pmx_just_sign.svg"),
            os.path.join("staticfiles", "icons", "pmx_just_x_sign.svg"),
        ]
        logo_path_to_use = None
        for candidate in logo_candidates:
            if os.path.exists(candidate):
                logo_path_to_use = candidate
                break
        if logo_path_to_use:
            try:
                target_w, target_h = 37, 80
                y_pos = PAGE_HEIGHT - target_h
                if logo_path_to_use.lower().endswith(".svg"):
                    drawing = svg2rlg(logo_path_to_use)
                    if drawing:
                        drawing.scale(target_w / drawing.width, target_h / drawing.height)
                        drawing.width = target_w
                        drawing.height = target_h
                        renderPDF.draw(drawing, canvas, x=32, y=y_pos)
                else:
                    canvas.drawImage(
                        logo_path_to_use,
                        x=-2,
                        y=y_pos,
                        width=target_w,
                        height=target_h,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
            except Exception as e:
                print("Header logo load failed:", e)
        canvas.rect(0, FOOTER_HEIGHT, AVAILABLE_WIDTH, PAGE_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT)
        # Right-aligned site text with specified style and padding
        text = "www.pmxhealth.com"
        padding = 32
        line_height = 18  # for consistency with CSS line-height
        canvas.setFont(FONT_INTER_REGULAR, FONT_SIZE_MEDIUM)  # Inter, 12, regular
        canvas.setFillColor(PMX_GREEN)  # var(--Brand-500, #00625B)
        # Align to the right edge with 32pt padding, and position vertically with 32pt top padding
        canvas.drawRightString(PAGE_WIDTH - padding, PAGE_HEIGHT - padding - (line_height - FONT_SIZE_MEDIUM), text)
        canvas.restoreState()

    def draw_footer(self, canvas, doc):
        # if doc.page == 1:
        #     return

        canvas.saveState()
        # Bottom-left logo at 32 padding from left and bottom, with size 65x30
        logo_x, logo_y = 32, 25
        logo_width, logo_height = 65, 30
        logo = self.template._get_logo()

        if isinstance(logo, ThriveRoadmapOnlySVGImage):
            drawing = svg2rlg(logo.filename)
            if drawing:
                drawing.scale(logo_width / drawing.width, logo_height / drawing.height)
                renderPDF.draw(drawing, canvas, x=logo_x, y=logo_y)
        elif isinstance(logo, Image):
            canvas.drawImage(logo.filename, logo_x, logo_y, width=logo_width, height=logo_height, mask='auto')
        else:
            canvas.setFont(FONT_INTER_BOLD, 10)
            canvas.setFillColor(PMX_GREEN)
            canvas.drawString(logo_x, logo_y, "PMX Health")

        canvas.restoreState()

class NumberedCanvas(Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, total_pages):
        page_number = self.getPageNumber()
        # if page_number <= 2:
        #     return
        # if page_number == total_pages:
        #     return
        text = f"Page {page_number:02d} - {total_pages:02d}"
        font = FONT_INTER_REGULAR
        size = FONT_SIZE_SMALL  # 10pt
        text_width = stringWidth(text, font, size)
        self.setFont(font, size)
        self.setFillColor(colors.HexColor("#667085"))  # Grey-500
        padding = 32
        # Bottom-right placement with 32pt padding from right and bottom
        self.drawRightString(PAGE_WIDTH - padding, padding, text)

class VerticalLine(Flowable):
    def __init__(self, height, x_offset=0, line_color=PMX_GREEN, thickness=1):
        Flowable.__init__(self)
        self.height = height
        self.x_offset = x_offset
        self.line_color = line_color
        self.thickness = thickness
        self.width = 0

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self.line_color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(self.x_offset, 0, self.x_offset, self.height)
        self.canv.restoreState()

    def wrap(self, availWidth, availHeight):
        return 0, self.height

class SvgTitleRow(Flowable):
    def __init__(self, icon, text_para, gap=6, vertical_align="middle"):
        super().__init__()
        self.icon = icon
        self.text_para = text_para
        self.gap = gap
        self.vertical_align = vertical_align  # "middle" or "top"

        # Get icon dimensions
        self.icon_width = icon.width
        self.icon_height = icon.height

        # Wrap paragraph to compute height
        self.text_para.wrap(500, 0)
        self.text_width = self.text_para.width
        self.text_height = self.text_para.height

        # Determine total dimensions
        self.width = self.icon_width + self.gap + self.text_width
        self.height = max(self.icon_height, self.text_height)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        if str(self.vertical_align).lower() == "top":
            icon_y = self.height - self.icon_height
            text_y = self.height - self.text_height
        else:
            icon_y = (self.height - self.icon_height) / 2
            text_y = (self.height - self.text_height) / 2

        # Draw icon and text
        self.icon.drawOn(self.canv, 0, icon_y)
        self.text_para.drawOn(self.canv, self.icon_width + self.gap, text_y)

class ThriveRoadmapTemplate:
    def __init__(self,buffer):
        self.buffer = buffer
        self.styles = getSampleStyleSheet()
        self.base_path = Path("staticfiles/icons")
        self.init_styles()
        self.svg_dir = "staticfiles/icons/"
        self.doc = MyDocTemplate(buffer)

    def _get_logo(self):
        possible_paths = [
            self.base_path / "pmx_green_logo.svg",
            "staticfiles/reports/pmx_green_logo.svg",
            "staticfiles/icons/pmx_green_logo.svg",
        ]
        for logo_path in possible_paths:
            if os.path.exists(logo_path):
                try:
                    svg = svg2rlg(logo_path)
                    if svg:
                        return ThriveRoadmapOnlySVGImage(str(logo_path), width=60)
                    return Image(str(logo_path), width=60, height=60)
                except Exception:
                    continue
        return Paragraph(
            "PMX Health",
            ParagraphStyle(
                "LogoPlaceholder",
                fontName=FONT_INTER_BOLD,
                fontSize=14,
                textColor=PMX_GREEN,
                alignment=TA_LEFT,
            ),
        )
    
    def init_styles(self):
        # Ear screening styles
        self.styles.add(ParagraphStyle(
            name="ear_screening_title",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=12,
            leading=24,
            textColor=PMX_GREEN,
            backColor=None,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="ear_screening_unit",
            fontName=FONT_INTER_REGULAR,
            fontSize=8,
            leading=18,
            textColor=colors.HexColor("#667085"),
            spaceBefore=0,
            spaceAfter=0
        ))

        # Profile card styles
        self.styles.add(ParagraphStyle(
            name="profile_card_otherstyles",
            fontName=FONT_RALEWAY_MEDIUM,
            fontSize=30,
            leading=38,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))

        self.styles.add(ParagraphStyle(
            name="profile_card_name",
            fontName=FONT_INTER_REGULAR,
            fontSize=16,
            leading=24,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
            spaceAfter=0,
        ))

        # TOC styles
        self.styles.add(ParagraphStyle(
            name="TOCTitleStyle",
            fontName=FONT_RALEWAY_MEDIUM,
            fontSize=24,
            leading=28,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="TOCEntryText",
            fontName=FONT_INTER_REGULAR,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1F2937"),
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="toc_pagenum",
            fontName=FONT_INTER_REGULAR,
            fontSize=12,
            leading=16,
            textColor=PMX_GREEN,
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            "eye_screening_desc_style",
            fontName=FONT_INTER_REGULAR,
            fontSize=10,
            leading=16,  # line-height: 160% of 10px = 16px
            textColor=colors.HexColor("#667085"),
            spaceBefore=0,
            spaceAfter=0
        ))
        self.styles.add(ParagraphStyle(
            name="OptimizationPhasesStyle",
            fontName=FONT_INTER_REGULAR,                     # Make sure 'Inter' is registered, else fallback to 'Helvetica'
            fontSize=7.375,
            leading=10.536,                       # Line height
            textColor=colors.HexColor("#475467"),# Equivalent to var(--Gray-600)
            alignment=1,                          # 0=left, 1=center, 2=right, 4=justify
        ))
        self.styles.add(ParagraphStyle(
            "BiomarkersStyle",
            fontName=FONT_RALEWAY_MEDIUM,               
            fontSize=16,
            leading=24,                       
            textColor=PMX_GREEN   
        ))
        self.styles.add(ParagraphStyle(
            "bullet_after_text",
            fontName=FONT_INTER_REGULAR,                   # Make sure Inter-Regular is registered
            fontSize=12,
            leading=18,                         # Equivalent to line-height: 18px
            textColor=colors.HexColor("#003632"),     # Brand-800
            spaceBefore=0,
            spaceAfter=0,
        ))
        # Superfoods table styles
        self.styles.add(ParagraphStyle(
            "SuperfoodsHeaderStyle",
            fontName=FONT_RALEWAY_BOLD,
            fontSize=10,
            leading=14,
            textColor=PMX_GREEN,
        ))
        self.styles.add(ParagraphStyle(
            "SuperfoodsCellStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=8,
            leading=14,
            textColor=PMX_GREEN,
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
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style = [
            # Headers
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, 0), PMX_GREEN),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), FONT_INTER_BOLD),
            ("FONTSIZE", (0, 0), (-1, 0), FONT_SIZE_MEDIUM),
            ("BOTTOMPADDING", (0, 0), (-1, 0), TABLE_HEADER_PADDING),
            ("TOPPADDING", (0, 0), (-1, 0), TABLE_HEADER_PADDING),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor('#00625B')),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),  
            ("ALIGN", (1, 1), (1, -1), "CENTER"),  
            ("ALIGN", (2, 1), (2, -1), "CENTER"),  
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -2), FONT_INTER_REGULAR),
            ("FONTSIZE", (0, 1), (-1, -1), FONT_SIZE_SMALL),
            ("TOPPADDING", (0, 1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            ("RIGHTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            # Grid and Borders
            ("GRID", (0, 0), (-1, -1), 0.5, PMX_TABLE_GRID),
            ("LINEBELOW", (0, 0), (-1, 0), 0.01, PMX_GREEN),
            ("LINEAFTER", (0, 0), (0, -1), 0.01, PMX_GREEN),
            ("LINEAFTER", (1,0), (1, -1), 0.01, PMX_GREEN),
            # Rounded Corners
            ("ROUNDEDCORNERS", [16, 16, 16, 16]),
            ("FONTNAME", (0, -1), (0, -1), FONT_INTER_BOLD),
            ("BOX", (0, 0), (-1, -1), 0.01, PMX_GREEN, None, None, "round"),
        ]

        # Add alternate row coloring starting from first data row (index 1)
        for i in range(1, len(table_data)):
            style.extend([("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F2F4F7")),("TEXTCOLOR", (0, i), (0, i), colors.HexColor('#00625B')),("FONTNAME", (0, i), (-1, i), FONT_INTER_BOLD)])
                

        table.setStyle(TableStyle(style))
        return table

    def svg_icon(self, path, width=12, height=12):
        try:
            drawing = svg2rlg(path)
            if drawing is None:
                raise FileNotFoundError(f"SVG file '{path}' could not be loaded or is invalid.")
        except Exception as e:
            print(f"Error loading SVG: {e}")
            drawing = Drawing(width, height)
        
        original_width = drawing.width or 1
        original_height = drawing.height or 1
        drawing.scale(width / original_width, height / original_height)
        drawing.width = width
        drawing.height = height
        return drawing
    
    def add_bottom_left_image(self, image_path,x,y, width=202, height=225) -> list:
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
                return 0, 0  

            def draw(self):
                try:
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

    def get_dynamic_col_width(self, text, font_name=FONT_INTER_REGULAR, font_size=10, icon_width=24):
        """
        Calculates total column width for icon + text + small buffer.
        All units are in points, not mm.
        """
        text_width = stringWidth(text, font_name, font_size)
        padding_buffer = 4  
        return icon_width + text_width + padding_buffer

    def icon_with_text(self, icon_path, text, style, icon_width=24, icon_height=24):
        """
        Builds a row [icon | text] with precise sizing.
        All dimensions are in points.
        """
        icon = self.svg_icon(icon_path, width=icon_width, height=icon_height)
        para = Paragraph(text, style)
        
        return Table(
            [[icon, para]],
            colWidths=[
                icon_width,
                self.get_dynamic_col_width(text, style.fontName, style.fontSize, icon_width)
            ],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )

    def get_user_profile_card(self, user_profile_card: dict) -> Table:
        icon_paths = {
            "avatar": "staticfiles/icons/Dp.png",
            "id": "staticfiles/icons/pmx_x.svg",
            "gender": "staticfiles/icons/gender_male.svg",
            "location": "staticfiles/icons/location.svg",
            "briefcase": "staticfiles/icons/business.svg",
            "dob_calendar": "staticfiles/icons/dob_calendar.svg",
            "doa_calendar": "staticfiles/icons/calendar.svg",
            "diet": "staticfiles/icons/food.svg",
        }

        widths_heights = {
            "id": {"width": 24, "height": 24},
            "gender": {"width": 16, "height": 16},
            "location": {"width": 16, "height": 16},
            "briefcase": {"width": 16, "height": 16},
            "dob_calendar": {"width": 16, "height": 16},
            "doa_calendar": {"width": 16, "height": 16},
            "diet": {"width": 16, "height": 24},
        }

        # Text values
        name = user_profile_card.get("name", "")
        user_id = user_profile_card.get("id", "")
        gender = user_profile_card.get("gender", "")
        if gender.lower() == "female":
            icon_paths["gender"] = "staticfiles/icons/gender_female.svg"
        location = f"{user_profile_card.get('city', '')} - {user_profile_card.get('pincode', '')}"
        occupation = user_profile_card.get("occupation", "")
        dob = f"D.O.B - {user_profile_card.get('dob', '')}"
        doa = f"D.O.A - {user_profile_card.get('doa', '')}"
        diet = user_profile_card.get("diet", "")
        allergies = f"Allergies - {user_profile_card.get('allergies', '')}"

        style = self.styles["profile_card_name"]

        # Small helper to build a cell and its exact dynamic width
        def build_cell(icon_key: str, text_value: str, size_key: str):
            icon_size = widths_heights[size_key]
            cell = self.icon_with_text(
                icon_paths[icon_key],
                text_value,
                style,
                icon_width=icon_size["width"],
                icon_height=icon_size["height"],
            )
            width = self.get_dynamic_col_width(
                text_value,
                font_name=style.fontName,
                font_size=style.fontSize,
                icon_width=icon_size["width"],
            )
            return cell, width

        # Name row
        name_para = Paragraph(name, self.styles["profile_card_otherstyles"])

        # ID row
        id_row = self.icon_with_text(
            icon_paths["id"],
            f"ID - {user_id}",
            style,
            icon_width=widths_heights["id"]["width"],
            icon_height=widths_heights["id"]["height"],
        )

        # Gender, Location, Occupation row
        gender_cell, gender_width = build_cell("gender", gender, "gender")
        location_cell, location_width = build_cell("location", location, "location")
        occupation_cell, occupation_width = build_cell("briefcase", occupation, "briefcase")

        line2 = Table(
            [[gender_cell, location_cell, occupation_cell]],
            colWidths=[gender_width, location_width, occupation_width],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        # DOB, DOA row
        dob_cell, dob_width = build_cell("dob_calendar", dob, "dob_calendar")
        doa_cell, doa_width = build_cell("doa_calendar", doa, "doa_calendar")
        line3 = Table(
            [[dob_cell, doa_cell]],
            colWidths=[dob_width, doa_width],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        # Diet and Allergies row (both use the same icon)
        diet_cell, diet_width = build_cell("diet", diet, "diet")
        allergies_cell, allergies_width = build_cell("diet", allergies, "diet")
        line4 = Table(
            [[diet_cell, allergies_cell]],
            colWidths=[diet_width, allergies_width],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        # Combine all text parts
        text_block = [[id_row], [name_para], [line2], [line3], [line4], [Spacer(1, 24)]]
        text_table = Table(
            text_block,
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        # Avatar Image
        avatar = Image(icon_paths["avatar"], width=100, height=100)
        avatar.hAlign = "LEFT"

        # Combine Avatar and Text in main layout
        final_table = Table(
            [[avatar, Spacer(1, 32), text_table]],
            colWidths=[100, 32, None],
            style=[
                ("VALIGN", (1, 0), (1, -1), "TOP"),
                ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ],
        )
        final_table2 = Table(
            [[final_table]],
            colWidths=[PAGE_WIDTH],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 32),
                ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ],
        )
        return final_table2

    def get_superfoods_table(self, items: list, columns: list | None = None) -> Table:
        """Builds a two-column table using provided items and columns.

        Default columns for superfoods:
        - category (width: 100)
        - what_to_eat (width: 430)
        Pass a different columns list to reuse for other sections with the same layout.
        """
        if columns is None:
            columns = [("category", 100), ("what_to_eat", 430)]

        header_cells = [
            Paragraph(col_key.replace("_", " ").capitalize(), self.styles["SuperfoodsHeaderStyle"]) for col_key, _ in columns
        ]

        table_data = [header_cells]

        for item in items or []:
            row_cells = []
            for col_key, _ in columns:
                value = item.get(col_key, "")
                row_cells.append(Paragraph(str(value), self.styles["SuperfoodsCellStyle"]))
            table_data.append(row_cells)

        col_widths = [w for _, w in columns]
        return self._build_styled_table(table_data, col_widths)

    def get_reasons_to_skip_table(self, reasons_to_skip: list) -> Table:
        """Builds the Reasons to Skip table using the reusable two-column builder."""
        columns = [("category", 100), ("items_to_skip", 430)]
        return self.get_superfoods_table(reasons_to_skip, columns=columns)

    def get_anti_inflammatory_table(self, anti_inflammatory: list) -> Table:
        """Build a table for anti-inflammatory plan.

        Structure of input:
        [
          {
            "week": "Week 1 & 2",
            "week_data": [
               {"category": "...", "foods_to_exclude": "..."},
               ...
            ]
          },
          ...
        ]

        Column widths (points):
        - week: 65
        - category: 144
        - foods_to_exclude: 298
        """
        columns = [
            ("week", 65),
            ("category", 144),
            ("foods_to_exclude", 298),
        ]

        # Header row using Superfoods header style
        header_cells = [
            Paragraph(col_key.replace("_", " ").capitalize(), self.styles["SuperfoodsHeaderStyle"]) for col_key, _ in columns
        ]
        table_data = [header_cells]

        # Build data rows and record span ranges for the week column
        span_commands = []
        current_row_index = 1  # account for header row at index 0

        for week_block in anti_inflammatory or []:
            week_label = week_block.get("week", "")
            entries = week_block.get("week_data", []) or []

            if not entries:
                # Single empty row for this week
                row = [
                    Paragraph(str(week_label), self.styles["SuperfoodsCellStyle"]),
                    Paragraph("", self.styles["SuperfoodsCellStyle"]),
                    Paragraph("", self.styles["SuperfoodsCellStyle"]),
                ]
                table_data.append(row)
                current_row_index += 1
                continue

            start_row = current_row_index
            for idx, entry in enumerate(entries):
                category_text = entry.get("category", "")
                foods_text = entry.get("foods_to_exclude", "")

                week_cell = (
                    Paragraph(str(week_label), self.styles["SuperfoodsCellStyle"]) if idx == 0 else ""
                )
                row = [
                    week_cell,
                    Paragraph(str(category_text), self.styles["SuperfoodsCellStyle"]),
                    Paragraph(str(foods_text), self.styles["SuperfoodsCellStyle"]),
                ]
                table_data.append(row)
                current_row_index += 1

            # Add span for the week column over this block's rows
            end_row = current_row_index - 1
            if end_row >= start_row:
                span_commands.append(("SPAN", (0, start_row), (0, end_row)))
                # optionally vertically center the spanned week cell
                span_commands.append(("VALIGN", (0, start_row), (0, end_row), "MIDDLE"))

        col_widths = [w for _, w in columns]
        table = self._build_styled_table(table_data, col_widths)
        if span_commands:
            table.setStyle(TableStyle(span_commands))
        return table
    
    def get_optimization_phases(self, optimization_phases: dict):
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = optimization_phases.get("header", "")
        title_data = optimization_phases.get("header_data", "")
        optimization_phases_data_ = optimization_phases.get("optimization_phases_data", "")
        

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 8))
        section.append(Paragraph(title_data, self.styles["eye_screening_desc_style"]))
        section.append(Spacer(1, 17))
        
        left_col_width = 126
        gap_between_columns = 16
        right_col_width = 322  # width allocated to the right column

        for item in optimization_phases_data_:
            # Left stack (vertical)
            left_stack = []

            day = item.get("day", "00 Phase")
            name = item.get("name", "")
            duration = item.get("duration", "")
            data = item.get("data", "")

            icon_path = os.path.join(svg_dir, "supplement_icon.png")
            icon = Image(icon_path, width=16, height=16)
            left_stack.append(icon)
            left_stack.append(Spacer(1,8))

            text_1 = Paragraph(
                f'<font fontName={FONT_INTER_BOLD}>{day}</font>',
                self.styles["OptimizationPhasesStyle"]
            )
            left_stack.append(text_1)

        
            # Use nested table to keep pill and paragraph side by side in the right column
            
            name_para = Paragraph(name, self.styles["BiomarkersStyle"])
            duration_para = Paragraph(f'<font color="#4DAEA6">{duration}</font>', self.styles["bullet_after_text"])
        
            name_width = stringWidth(name, self.styles["BiomarkersStyle"].fontName, self.styles["BiomarkersStyle"].fontSize)
            # Combine pill and para horizontally using inner table
            if data:
                left_stack.append(VerticalLine(height=142))
                remaining_width = max(50, right_col_width - name_width - 7)
                inner_table = Table(
                    [
                        [name_para, Spacer(7, 1), duration_para],
                        [Paragraph(data, self.styles["eye_screening_desc_style"])]
                    ],
                    colWidths=[name_width, 7, remaining_width]
                )
                inner_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("SPAN", (0, 1), (-1, 1)),
                ]))
            else:
                remaining_width = max(50, right_col_width - name_width - 7)
                inner_table = Table(
                    [
                        [name_para, Spacer(7, 1), duration_para]
                    ],
                    colWidths=[name_width, 7, remaining_width]
                )
                inner_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0)
                ]))
            
            # Combine everything into the final row table with proper column spacing
            final_table = Table(
                [[left_stack, Spacer(gap_between_columns, 1), inner_table]],
                colWidths=[left_col_width, gap_between_columns, right_col_width]
            )

            final_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (0, -1), "TOP"),
                ("VALIGN", (1, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ]))

            # Add to section
            section.append(final_table)
            section.append(Spacer(1, 8))  # Optional gap between entries

        section.append(Indenter(left=-32, right=-32))

        return section

    def build_toc_table(self, toc_data):
        # TOC disabled – return empty list
        return []

    def generate(self, data: dict) -> list:
        story = []
        
        story.append(Indenter(left=32, right=32))
        user_profile_card=data.get("user_profile_card",{})
        if user_profile_card:
            story.append(self.get_user_profile_card(user_profile_card))
            # TOC disabled – no hidden TOC paragraphs
        
        optimization_phases=data.get("optimization_phases",{})
        if optimization_phases:
            story.append(Spacer(1, 16))
            story.extend(self.get_optimization_phases(optimization_phases))

        # Superfoods to prioritise table
        superfoods = data.get("superfoods_to_priortise", [])
        if superfoods:
            story.append(PageBreak())
            # Icon + title row
            food_icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
            title_para = Paragraph("Superfoods to Prioritise", self.styles["TOCTitleStyle"])
            title_row = SvgTitleRow(food_icon, title_para, gap=8)
            story.append(title_row)
            story.append(Spacer(1, 8))
            story.append(self.get_superfoods_table(superfoods))
        
        anti_inflammatory = data.get("anti_inflammatory", [])
        if anti_inflammatory:
            story.append(PageBreak())
            # Icon + title row
            food_icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
            title_para = Paragraph("Phase 1 <br/>Anti inflammatory - 8 Weeks ", self.styles["TOCTitleStyle"])
            title_row = SvgTitleRow(food_icon, title_para, gap=8, vertical_align="top")
            story.append(title_row)
            story.append(Spacer(1, 8))
            story.append(self.get_anti_inflammatory_table(anti_inflammatory))
        
        reasons = data.get("reasons_to_skip", [])
        if reasons:
            story.append(PageBreak())
            # Icon + title row (red color, nottoeat.svg 34x34)
            nottoeat_icon = self.svg_icon("staticfiles/icons/nottoeat.svg", width=34, height=34)
            title_para = Paragraph('<font color="#F04438">Reasons to Skip</font>', self.styles["TOCTitleStyle"])
            title_row = SvgTitleRow(nottoeat_icon, title_para, gap=8)
            story.append(title_row)
            story.append(Spacer(1, 8))
            story.append(self.get_reasons_to_skip_table(reasons))
        return story


app = FastAPI()

@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    data = await request.json()

    buffer = io.BytesIO()
    template = ThriveRoadmapTemplate(buffer)
    renderer = ThrivePageRenderer(template)

    PAGE_WIDTH, PAGE_HEIGHT = A4
    HEADER_HEIGHT = 80
    FOOTER_HEIGHT = 80
    svg_dir = "staticfiles/icons/"

    # Define custom doc
    doc = MyDocTemplate(buffer, pagesize=A4, leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)

    # Frames
    frame = Frame(
        x1=0, y1=FOOTER_HEIGHT, width=PAGE_WIDTH,
        height=PAGE_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT,
        id='main', leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0,
    )
    
    # Page templates
    doc.addPageTemplates([
        PageTemplate(id='main', frames=[frame], onPage=renderer.draw_header, onPageEnd=renderer.draw_footer),
    
    ])

    # Single-pass build without TOC
    story = template.generate(data)
    doc.build(story, canvasmaker=NumberedCanvas)
    with open("nutirtion_report.pdf", "wb") as f:
        f.write(buffer.getvalue())

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "inline; filename=styled_output.pdf"
    })

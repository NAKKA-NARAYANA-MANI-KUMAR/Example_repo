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
from reportlab.graphics.shapes import Drawing,Rect, String, Line,Circle
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

class RoundedBox(Flowable):
    def __init__(self, width=A4[0] - 64, height=None, content=None, corner_radius=8, border_radius=0.4, stroke_color=PMX_GREEN, fill_color=colors.white, inner_padding: float = 0):
        super().__init__()
        self.width = width
        self.height = height
        self.content = content
        self.corner_radius = corner_radius
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.border_radius = border_radius
        self.inner_padding = inner_padding

    def wrap(self, availWidth, availHeight):
        pad = self.inner_padding or 0
        inner_w = max(0, (availWidth or 0) - 2 * pad)
        inner_h = max(0, (availHeight or 0) - 2 * pad)
        if self.content:
            content_width, content_height = self.content.wrap(inner_w, inner_h)
        else:
            content_width, content_height = 0, 0
        self.width = self.width or (content_width + 2 * pad)
        self.height = self.height or (content_height + 2 * pad)
        return self.width, self.height

    def draw(self):
        pad = self.inner_padding or 0
        inner_w = max(0, self.width - 2 * pad)
        inner_h = max(0, self.height - 2 * pad)
        self.canv.saveState()
        self.canv.setFillColor(self.fill_color)
        self.canv.setStrokeColor(self.stroke_color)
        self.canv.setLineWidth(self.border_radius)
        self.canv.roundRect(0, 0, self.width, self.height, self.corner_radius, fill=1, stroke=1)
        if self.content:
            # Measure content height for vertical centering within inner padding box
            content_w, content_h = self.content.wrap(inner_w, inner_h)
            y_offset = pad + max(0, (inner_h - content_h) / 2)
            self.content.drawOn(self.canv, pad, y_offset)
        self.canv.restoreState()

class RoundedPill(Flowable):
    def __init__(
        self,
        text,
        bg_color,
        radius=None,
        width=None,
        height=None,
        font_size=8,
        text_color=colors.white,
        border_color=None,
        border_width=0.2,
        font_name=FONT_INTER_SEMI_BOLD,
        icon_path=None,
        icon_width=0,
        icon_height=0,
        icon_text_padding=4,
        left_padding=8,
        right_padding=8,
        top_padding=6,
        bottom_padding=6,
    ):
        super().__init__()
        self.text = str(text)
        self.bg_color = bg_color
        self.radius = radius
        self.width = width
        self.height = height
        self.font_size = font_size
        self.text_color = text_color
        self.border_color = border_color
        self.border_width = border_width
        self.font_name = font_name

        # Padding
        self.left_padding = left_padding
        self.right_padding = right_padding
        self.top_padding = top_padding
        self.bottom_padding = bottom_padding

        # Icon setup
        self.icon_path = icon_path
        self.icon_width = icon_width
        self.icon_height = icon_height
        self.icon_text_padding = icon_text_padding
        self.icon_drawing = None

        if self.icon_path and os.path.exists(self.icon_path):
            try:
                drawing = svg2rlg(self.icon_path)
                if drawing.width > 0 and drawing.height > 0:
                    scale_x = self.icon_width / drawing.width
                    scale_y = self.icon_height / drawing.height
                    drawing.scale(scale_x, scale_y)
                    self.icon_drawing = drawing
            except Exception as e:
                print(f"Error loading SVG: {e}")
                self.icon_drawing = None

    def wrap(self, availWidth, availHeight):
        # Measure text
        text_width = stringWidth(self.text, self.font_name, self.font_size)
        # Font metrics for more reliable vertical sizing
        try:
            ascent = pdfmetrics.getAscent(self.font_name) / 1000.0 * self.font_size
            descent = abs(pdfmetrics.getDescent(self.font_name)) / 1000.0 * self.font_size
        except Exception:
            ascent = self.font_size * 0.8
            descent = self.font_size * 0.2
        text_box_h = ascent + descent

        content_width = text_width + self.left_padding + self.right_padding

        if self.icon_drawing:
            content_width += self.icon_width + self.icon_text_padding

        # Height estimate (ensure room for font metrics and optional icon)
        content_height = max(text_box_h, self.font_size, self.icon_height) + self.top_padding + self.bottom_padding

        # Use fixed width/height if given, else use computed
        self.width = self.width if self.width is not None else content_width
        self.height = self.height if self.height is not None else content_height
        self.radius = self.radius if self.radius is not None else self.height / 2

        return self.width, self.height

    def draw(self):
        self.canv.saveState()

        # Rounded background
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

        # Text measurement
        self.canv.setFont(self.font_name, self.font_size)
        text_width = self.canv.stringWidth(self.text, self.font_name, self.font_size)

        content_width = text_width
        if self.icon_drawing:
            content_width += self.icon_width + self.icon_text_padding

        # Honor left/right padding when centering horizontally
        available_w = max(0, self.width - self.left_padding - self.right_padding)
        start_x = self.left_padding + max(0, (available_w - content_width) / 2)

        # Honor top/bottom padding when centering vertically
        content_h = max(0, self.height - self.top_padding - self.bottom_padding)
        center_y = self.bottom_padding + content_h / 2

        # Draw icon
        if self.icon_drawing:
            icon_y = center_y - self.icon_height / 2
            renderPDF.draw(self.icon_drawing, self.canv, start_x, icon_y)
            start_x += self.icon_width + self.icon_text_padding

        # Draw text baseline centered in padded area using font ascent/descent
        try:
            ascent = pdfmetrics.getAscent(self.font_name) / 1000.0 * self.font_size
            descent = abs(pdfmetrics.getDescent(self.font_name)) / 1000.0 * self.font_size
        except Exception:
            ascent = self.font_size * 0.8
            descent = self.font_size * 0.2
        text_box_h = ascent + descent
        text_y = self.bottom_padding + max(0, (content_h - text_box_h) / 2) + descent
        self.canv.setFillColor(self.text_color)
        self.canv.drawString(start_x, text_y, self.text)

        self.canv.restoreState()

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
        # canvas.rect(0, FOOTER_HEIGHT, AVAILABLE_WIDTH, PAGE_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT)
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
        # Small section title style for protein headings
        self.styles.add(ParagraphStyle(
            name="SectionSmallRalewayBold",
            fontName=FONT_RALEWAY_BOLD,
            fontSize=15.079,
            leading=22.619,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
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
        # Protein table: special style for food_item column
        self.styles.add(ParagraphStyle(
            "ProteinFoodItemCellStyle",
            fontName=FONT_RALEWAY_BOLD,
            fontSize=8.989,
            leading=12.584,
            textColor=PMX_GREEN,
        ))
        # Meal Timeline styles
        self.styles.add(ParagraphStyle(
            name="MealTimelineTimeStyle",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=12.85,
            leading=17.991,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
            wordWrap='CJK',
        ))
        self.styles.add(ParagraphStyle(
            name="MealTimelineTitleStyle",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=10,
            leading=14,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="MealTimelineDescStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=8,
            leading=8,
            textColor=colors.HexColor("#667085"),
            alignment=TA_LEFT,
        ))
        # Weekly Meal Plan styles
        self.styles.add(ParagraphStyle(
            name="WeeklyMealHeaderStyle",
            fontName=FONT_RALEWAY_BOLD,
            fontSize=10,
            leading=14,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="WeeklyMealCellStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=8,
            leading=14,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))
        # Practices to Follow (bullets) styles
        self.styles.add(ParagraphStyle(
            name="PracticeHeaderMediumStyle",
            fontName=FONT_RALEWAY_MEDIUM,
            fontSize=16,
            leading=24,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))
        self.styles.add(ParagraphStyle(
            name="PracticeBulletStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=10,
            leading=16,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
            wordWrap='CJK',
        ))
        # Foods to Reintroduce styles
        self.styles.add(ParagraphStyle(
            name="ReintroItemTitleStyle",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=12,
            leading=19.885,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
            wordWrap='CJK',
        ))
        self.styles.add(ParagraphStyle(
            name="ReintroQtyStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=9.2,
            leading=11.363,
            textColor=colors.HexColor("#667085"),
            alignment=TA_LEFT,
            wordWrap='CJK',
        ))
        # Food Items: section header style (bullet + title)
        self.styles.add(ParagraphStyle(
            name="FoodSectionHeaderStyle",
            fontName=FONT_RALEWAY_BOLD,
            fontSize=25.099,
            leading=31.539,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))
        # Food Items: title style
        self.styles.add(ParagraphStyle(
            name="FoodItemTitleStyle",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=15.439,
            leading=21.614,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))
        # Food Items: description style
        self.styles.add(ParagraphStyle(
            name="FoodItemDescStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=10,
            leading=12.351,
            textColor=colors.HexColor("#667085"),
            alignment=TA_LEFT,
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
            # Rounded Corners
            ("ROUNDEDCORNERS", [16, 16, 16, 16]),
            ("FONTNAME", (0, -1), (0, -1), FONT_INTER_BOLD),
            ("BOX", (0, 0), (-1, -1), 0.01, PMX_GREEN, None, None, "round"),
        ]

        # Ensure all vertical lines are Brand Green between every column
        num_cols = len(col_widths)
        for col_idx in range(num_cols - 1):
            style.append(("LINEAFTER", (col_idx, 0), (col_idx, -1), 0.01, PMX_GREEN))

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
                # Apply special style for food_item column when present
                if col_key == "food_item":
                    row_cells.append(Paragraph(str(value), self.styles["ProteinFoodItemCellStyle"]))
                else:
                    row_cells.append(Paragraph(str(value), self.styles["SuperfoodsCellStyle"]))
            table_data.append(row_cells)

        col_widths = [w for _, w in columns]
        return self._build_styled_table(table_data, col_widths)

    def get_reasons_to_skip_table(self, reasons_to_skip: list) -> Table:
        """Builds the Reasons to Skip table using the reusable two-column builder."""
        columns = [("category", 100), ("items_to_skip", 430)]
        return self.get_superfoods_table(reasons_to_skip, columns=columns)

    def get_protein_table(self, items: list) -> Table:
        """Builds a two-column protein table with widths: 141 and 116."""
        columns = [("food_item", 141), ("Protien_per_100g", 116)]
        return self.get_superfoods_table(items, columns=columns)

    def get_side_by_side_protein_tables(self, meat_poultry_food: list, sea_food: list) -> Table:
        """Renders two protein tables side by side (left: meat/poultry, right: sea food).

        Each table width = 141 + 116 = 257. Gap between tables = 16. Total = 530 to fit current layout width.
        """
        left_table = self.get_protein_table(meat_poultry_food or [])
        right_table = self.get_protein_table(sea_food or [])

        container = Table(
            [[left_table, Spacer(16, 1), right_table]],
            colWidths=[257, 16, 257],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )
        return container

    def _resolve_nutrition_image_path(self, title: str) -> str | None:
        safe = (title or "").strip().lower().replace(" ", "_")
        candidates = [
            os.path.join("staticfiles", "nutrition_images", f"{safe}.png"),
            os.path.join("staticfiles", "nutrition_images_png", f"{safe}.png"),
            os.path.join("staticfiles", "nutrition_images", f"{safe}.svg"),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _build_reintroduce_card(self, item: dict) -> RoundedBox:
        # Left image 47.4 x 57.4 from nutrition_images by item
        img_w, img_h = 47.4, 57.4
        title = item.get("item", "")
        resolved_path = self._resolve_nutrition_image_path(title)
        try:
            if resolved_path and resolved_path.lower().endswith(".png"):
                left_img = Image(resolved_path, width=img_w, height=img_h)
            elif resolved_path and resolved_path.lower().endswith(".svg"):
                left_img = self.svg_icon(resolved_path, width=img_w, height=img_h)
            else:
                left_img = Drawing(img_w, img_h)
        except Exception:
            left_img = Drawing(img_w, img_h)

        # Right stack: title, quantity, pill (calories)
        inner_pad = 10
        right_w = 172 - 2*inner_pad - 16 - img_w  # box width - inner padding - gap - left image
        title_para = Paragraph(title, self.styles["ReintroItemTitleStyle"])
        qty_para = Paragraph(item.get("quantity", ""), self.styles["ReintroQtyStyle"])

        # Rounded pill for calories
        pill_text = str(item.get("calories", "")).strip()
        pill = RoundedPill(
            text=pill_text,
            bg_color=colors.HexColor("#E6F4F3"),
            border_color=colors.HexColor("#26968D"),
            border_width=0.184,
            font_name=FONT_INTER_REGULAR,
            font_size=8,
            text_color=colors.HexColor("#003632"),
            radius=42.892 / 2,
            left_padding=7,
            right_padding=7,
            top_padding=5,
            bottom_padding=5,
        )

        # Constrain text within right_w using a KeepInFrame to avoid overflow
        text_block = Table(
            [[title_para], [qty_para]],
            colWidths=[right_w],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )
        kif = KeepInFrame(right_w, 1000, content=[text_block], hAlign='LEFT', mode='shrink')

        right_stack = Table(
            [[kif], [Spacer(1, 7)], [pill]],
            colWidths=[right_w],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        content = Table(
            [[left_img, Spacer(16, 1), right_stack]],
            colWidths=[img_w, 16, right_w],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        return RoundedBox(
            width=172,
            height=None,
            content=content,
            corner_radius=12.351,
            border_radius=0.772,
            stroke_color=Color(0/255, 62/255, 57/255, alpha=0.56),
            fill_color=colors.HexColor("#F2F4F7"),
            inner_padding=10,
        )

    def get_foods_to_reintroduce_section(self, foods_to_reintroduce: dict) -> list:
        section = []
        # Header
        icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
        title_para = Paragraph("Foods to Reintroduce", self.styles["TOCTitleStyle"])
        section.append(SvgTitleRow(icon, title_para, gap=8))
        section.append(Spacer(1, 8))

        # For each category, render header and cards grid (3 per row)
        for category, items in (foods_to_reintroduce or {}).items():
            if not isinstance(items, list):
                continue
            # Category header
            cat_label = category.replace("_", " ").title()
            bullet = self.svg_icon("staticfiles/icons/bullet.svg", width=16, height=16)
            section.append(SvgTitleRow(bullet, Paragraph(cat_label, self.styles["SectionSmallRalewayBold"]), gap=6))
            section.append(Spacer(1, 6))

            cards = [self._build_reintroduce_card(it) for it in items]
            rows = []
            i = 0
            while i < len(cards):
                row_cards = [cards[i]]
                if i + 1 < len(cards):
                    row_cards.append(cards[i+1])
                else:
                    row_cards.append("")
                if i + 2 < len(cards):
                    row_cards.append(cards[i+2])
                else:
                    row_cards.append("")

                # Measure and normalize heights so all three cards in the row have equal height
                measured_heights = []
                for rc in row_cards:
                    if isinstance(rc, RoundedBox):
                        rc.wrap(172, 100000)  # force compute height based on content
                        measured_heights.append(rc.height or 0)
                    else:
                        measured_heights.append(0)
                max_h = max(measured_heights) if measured_heights else 0
                normalized_cells = []
                for idx, rc in enumerate(row_cards):
                    if isinstance(rc, RoundedBox):
                        rc.height = max_h
                        normalized_cells.append(rc)
                    else:
                        normalized_cells.append(Spacer(172, max(1, max_h)))

                rows.append([normalized_cells[0], Spacer(12, 1), normalized_cells[1], Spacer(12, 1), normalized_cells[2]])
                i += 3

            grid = Table(
                rows or [[Spacer(172, 1), Spacer(12, 1), Spacer(172, 1), Spacer(12, 1), Spacer(172, 1)]],
                colWidths=[172, 12, 172, 12, 172],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ],
            )
            section.append(grid)
            section.append(Spacer(1, 10))

        return section

    def _build_food_item_card(self, item: dict) -> RoundedBox:
        # Left image (PNG preferred): 66 x 80
        left_w, left_h = 66, 80
        resolved_path = self._resolve_nutrition_image_path(item.get("title", ""))
        try:
            if resolved_path and resolved_path.lower().endswith(".png"):
                left_img = Image(resolved_path, width=left_w, height=left_h)
            elif resolved_path and resolved_path.lower().endswith(".svg"):
                left_img = self.svg_icon(resolved_path, width=left_w, height=left_h)
            else:
                left_img = Drawing(left_w, left_h)
        except Exception:
            left_img = Drawing(left_w, left_h)

        # Right stack (title + description) with fixed width 151 (fits 2 cards per row)
        right_w = 151
        title_para = Paragraph(item.get("title", ""), self.styles["FoodItemTitleStyle"])
        desc_para = Paragraph(item.get("title_data", ""), self.styles["FoodItemDescStyle"])
        right_stack = Table(
            [[title_para], [desc_para]],
            colWidths=[right_w],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        content_w = left_w + 16 + right_w
        content = Table(
            [[left_img, Spacer(16, 1), right_stack]],
            colWidths=[left_w, 16, right_w],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ],
        )

        # Box total width 257 to allow 2 boxes + 16 gap across 531 content width
        return RoundedBox(width=content_w + 24, height=None, content=content, corner_radius=16, border_radius=0.4, stroke_color=PMX_GREEN, fill_color=colors.white)

    def get_food_items_section(self, food_items: dict) -> list:
        section = []
        
        # Render each key as a header + list of cards
        for key in (food_items or {}).keys():
            items = food_items.get(key, []) or []
            if not isinstance(items, list):
                continue
            # Header row: bullet.svg + title
            display_title = str(key).replace("_", " ").title()
            bullet_icon = self.svg_icon(os.path.join("staticfiles", "icons", "bullet.svg"), width=24, height=24)
            header_para = Paragraph(display_title, self.styles["FoodSectionHeaderStyle"])
            section.append(SvgTitleRow(bullet_icon, header_para, gap=8))
            section.append(Spacer(1, 8))

            # Cards as 2 per row grid
            cards = [self._build_food_item_card(it) for it in items]
            rows = []
            i = 0
            while i < len(cards):
                left_card = cards[i]
                right_card = cards[i+1] if i + 1 < len(cards) else ""
                rows.append([left_card, Spacer(16, 1), right_card])
                i += 2
            if rows:
                rows_table = Table(
                    rows,
                    colWidths=[257, 16, 257],
                    style=[
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ],
                )
                section.append(rows_table)
                section.append(Spacer(1, 10))

        return section

    def _build_meal_card(self, item: dict) -> RoundedBox:
        # Image (PNG preferred): 36 x 44
        img_w, img_h = 36, 44
        resolved_path = self._resolve_nutrition_image_path(item.get("title", ""))
        try:
            if resolved_path and resolved_path.lower().endswith(".png"):
                left_img = Image(resolved_path, width=img_w, height=img_h)
            elif resolved_path and resolved_path.lower().endswith(".svg"):
                left_img = self.svg_icon(resolved_path, width=img_w, height=img_h)
            else:
                left_img = Drawing(img_w, img_h)
        except Exception:
            left_img = Drawing(img_w, img_h)

        right_w = 98
        title_para = Paragraph(item.get("title", ""), self.styles["MealTimelineTitleStyle"])
        desc_para = Paragraph(item.get("title_data", ""), self.styles["MealTimelineDescStyle"])

        # Keep paddings minimal to fit two cards inside right half
        right_stack = Table(
            [[title_para], [desc_para]],
            colWidths=[right_w],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        content = Table(
            [[left_img, Spacer(6, 1), right_stack]],
            colWidths=[img_w, 6, right_w],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ],
        )

        # Content width (inside padding)
        content_w = img_w + 6 + right_w  # 36 + 6 + 98 = 140
        # Add inner padding (8 on each side) to rounded box width so content fits without overflow
        card_width = content_w + 16
        return RoundedBox(
            width=card_width,
            height=None,
            content=content,
            corner_radius=12.351,
            border_radius=0.772,
            stroke_color=Color(0/255, 62/255, 57/255, alpha=0.56),
            fill_color=colors.HexColor("#F2F4F7"),
            inner_padding=8,
        )

    def get_meal_timeline_section(self, meal_timeline: list) -> list:
        section = []

        # Header
        food_icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
        title_para = Paragraph("Meal Timeline", self.styles["TOCTitleStyle"])
        section.append(SvgTitleRow(food_icon, title_para, gap=8))
        section.append(Spacer(1, 12))

        time_icon_path = os.path.join("staticfiles", "icons", "clock.svg")
        time_icon = self.svg_icon(time_icon_path, width=20, height=20)

        for block in meal_timeline or []:
            time_label = str(block.get("time", "")).strip()
            items = block.get("meal_data", []) or []

            # Fixed content widths with explicit outer paddings accounted in column widths
            left_content_w = 194
            right_content_w = 156 + 8 + 156  # two cards plus 8px gap
            left_col_w = 39 + left_content_w   # include 39 left padding
            right_col_w = right_content_w + 39 # include 39 right padding

            # Left stack: [time_icon | time text]
            time_para = Paragraph(time_label, self.styles["MealTimelineTimeStyle"])
            text_col_w = max(10, left_content_w - (20 + 6))
            time_kif = KeepInFrame(text_col_w, 1000, content=[time_para], hAlign='LEFT', mode='shrink')
            left_stack = Table(
                [[time_icon, Spacer(6, 1), time_kif]],
                colWidths=[20, 6, text_col_w],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )

            # Right grid: two cards per row with 8px gap between cards
            cards = [self._build_meal_card(it) for it in items]
            rows = []
            i = 0
            while i < len(cards):
                left_card = cards[i]
                right_card = cards[i+1] if i + 1 < len(cards) else ""
                rows.append([left_card, Spacer(8, 1), right_card])
                i += 2

            right_grid = Table(
                rows or [[Spacer(1, 1), Spacer(8, 1), Spacer(1, 1)]],
                colWidths=[156, 8, 156],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ],
            )

            # Flexible middle spacer ensures left aligns to left and right aligns to right with desired paddings
            total_needed = left_col_w + right_col_w
            middle_w = max(0, PAGE_WIDTH - total_needed)

            row_table = Table(
                [[left_stack, Spacer(middle_w, 1), right_grid]],
                colWidths=[left_col_w, middle_w, right_col_w],
                style=[
                    ("VALIGN", (0, 0), (0, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, -1), 39),     # left stack left padding 39
                    ("RIGHTPADDING", (-1, 0), (-1, -1), 39),  # right stack right padding 39
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )
            section.append(row_table)
            section.append(Spacer(1, 12))

        return section

    def get_weekly_mealplan_section(self, weekly_mealplan: list) -> list:
        section = []
        # Header row with icon
        food_icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
        title_para = Paragraph("Weekly Meal Plan", self.styles["TOCTitleStyle"])
        section.append(SvgTitleRow(food_icon, title_para, gap=8))
        section.append(Spacer(1, 8))

        # Column order and widths
        columns = [
            ("day", 40),
            ("early_morning", 75),
            ("breakfast", 100),
            ("lunch", 95),
            ("snack", 95),
            ("dinner", 95),
        ]

        # Build header using shared styles
        header_cells = [
            Paragraph(key.replace("_", " ").upper(), self.styles["SuperfoodsHeaderStyle"]) for key, _ in columns
        ]

        table_data = [header_cells]

        # Build rows using shared cell style
        for day_entry in weekly_mealplan or []:
            row = []
            for key, _ in columns:
                value = day_entry.get(key, "")
                if isinstance(value, list):
                    value = " + ".join(map(str, value))
                row.append(Paragraph(str(value), self.styles["SuperfoodsCellStyle"]))
            table_data.append(row)

        col_widths = [w for _, w in columns]
        table = self._build_styled_table(table_data, col_widths)

        section.append(table)
        return section

    def get_practices_to_follow_table(self, practices: list) -> Table:
        # Headers
        header_cells = [
            Paragraph("PRINCIPLE", self.styles["SuperfoodsHeaderStyle"]),
            Paragraph("GUIDELINE", self.styles["SuperfoodsHeaderStyle"]),
            Paragraph("SCIENTIFIC BASIS", self.styles["SuperfoodsHeaderStyle"]),
        ]
        table_data = [header_cells]

        # Rows
        for entry in practices or []:
            principle_para = Paragraph(str(entry.get("principle", "")), self.styles["SuperfoodsCellStyle"])
            guideline_para = Paragraph(str(entry.get("guideline", "")), self.styles["SuperfoodsCellStyle"])
            basis_para = Paragraph(str(entry.get("scientific_basis", "")), self.styles["SuperfoodsCellStyle"])
            table_data.append([principle_para, guideline_para, basis_para])

        col_widths = [92, 212, 242]
        return self._build_styled_table(table_data, col_widths)

    def get_practices_to_follow_bullets_section(self, info: dict) -> list:
        section = []
        # Header

        title = info.get("title", "")
        items = info.get("title_data", []) or []

        # Title paragraph
        section.append(Paragraph(title, self.styles["PracticeHeaderMediumStyle"]))
        section.append(Spacer(1, 6))

        # Bullets list
        # Custom bullet list to control spacing and color (circle, no underline)
        bullet_rows = []
        for it in items:
            bullet_para = Paragraph('<font color="#00625B">•</font>', self.styles["PracticeBulletStyle"])  # text bullet
            para = Paragraph(str(it), self.styles["PracticeBulletStyle"])  # no underline
            bullet_rows.append([bullet_para, Spacer(6, 1), para])

        if bullet_rows:
            bullet_table = Table(
                bullet_rows,
                colWidths=[10, 6, None],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ],
            )
            section.append(bullet_table)
        return section

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

        # Meal Timeline
        meal_timeline = data.get("meal_timeline", [])
        if meal_timeline:
            story.append(PageBreak())
            story.extend(self.get_meal_timeline_section(meal_timeline))

        # Weekly Meal Plan
        weekly_mealplan = data.get("weekly_mealplan", [])
        if weekly_mealplan:
            story.append(PageBreak())
            story.extend(self.get_weekly_mealplan_section(weekly_mealplan))
        
    
        # Protein tables: meat/poultry and sea food side by side
        meat = data.get("meat_poultry_food", [])
        sea = data.get("sea_food", [])
        if meat or sea:
            story.append(PageBreak())
            protein_icon = self.svg_icon("staticfiles/icons/bullet.svg", width=16, height=16)
            protein_title = Paragraph("Non - Vegetarian Protein Sources", self.styles["SectionSmallRalewayBold"])
            story.append(SvgTitleRow(protein_icon, protein_title, gap=8))
            story.append(Spacer(1, 20))
            sub_title = Paragraph("1. Meat, Poultry and seafood", self.styles["SectionSmallRalewayBold"])
            story.append(sub_title)

            story.append(Spacer(1, 8))
            story.append(self.get_side_by_side_protein_tables(meat, sea))
        
        # Food Items: Healthy Fats, Flours
        food_items = data.get("food_items", {})
        if food_items:
            story.append(PageBreak())
            food_icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
            title_para = Paragraph("Food Items", self.styles["TOCTitleStyle"])
            title_row = SvgTitleRow(food_icon, title_para, gap=8)
            story.append(title_row)
            story.append(Spacer(1, 16))
            story.extend(self.get_food_items_section(food_items))

        practices_to_follow = data.get("practices_to_follow", {})
        if practices_to_follow:
            story.append(PageBreak())
            food_icon = self.svg_icon("staticfiles/icons/food.svg", width=20, height=30)
            title_para = Paragraph("Practices to Follow ", self.styles["TOCTitleStyle"])
            title_row = SvgTitleRow(food_icon, title_para, gap=8)
            story.append(title_row)
            story.append(Spacer(1, 16))
            story.append(self.get_practices_to_follow_table(practices_to_follow))
        
         # Practices to Follow (bullet set with title + bullets)
        practices_to_follow_bullets = data.get("practices_to_follow_", {})
        if practices_to_follow_bullets:
            story.append(PageBreak())
            story.extend(self.get_practices_to_follow_bullets_section(practices_to_follow_bullets))
        
        # Foods to Reintroduce
        foods_to_reintroduce = data.get("foods_to_reintroduce", {})
        if foods_to_reintroduce:
            story.append(PageBreak())
            story.extend(self.get_foods_to_reintroduce_section(foods_to_reintroduce))       
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

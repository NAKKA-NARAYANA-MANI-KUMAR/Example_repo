# === main.py ===

import os
import io
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List

# ReportLab Core
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, Flowable, KeepTogether, PageBreak, SimpleDocTemplate, ListItem, ListFlowable,Indenter
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

# SVG Rendering
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg

# JSON Handling (optional if needed)
import json

# === Brand Colors ===
PMX_GREEN = colors.HexColor("#00625B")
PMX_GREEN_LIGHT = colors.HexColor("#EFE8CE")
PMX_BUTTON_BG = colors.HexColor("#E6F4F3")
PMX_BACKGROUND = colors.HexColor("#F8F9FA")
PMX_TABLE_HEADER_BG = colors.HexColor("#f5f5f5")
PMX_TABLE_GRID = colors.HexColor("#e0e0e0")
PMX_TABLE_HEADER_BORDER = colors.HexColor("#d0d0d0")
PMX_TABLE_ALTERNATE_ROW = colors.HexColor("#F0F2F6")

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
LEFT_MARGIN = 40
RIGHT_MARGIN = 20
AVAILABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
HEADER_HEIGHT = 80
FOOTER_HEIGHT = 80
TABLE_COL_NUMBER = 0.05
TABLE_PADDING = 8
TABLE_HEADER_PADDING = 12

svg_dir = "staticfiles/icons/"
# === Base Classes ===
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

    def __init__(self, page_width=A4[0], left_margin=0, thickness=0.001, color=colors.HexColor("#80C6C0"), spaceAfter=0):
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
        width, height = A4
        canvas.saveState()

        if doc.page == 1:
            # Draw glow text
            style = PDFStyleConfig()
            x = 100
            y = A4[1] - 200
            style.draw_glow_text(canvas, "Thrive Limitless", x, y)
            steps = int(height)
            for i in range(steps):
                pos = i / steps
                if pos <= 0.4529:
                    factor = pos / 0.4529
                    r, g, b = 0, int(32 * factor), int(30 * factor)
                else:
                    factor = (pos - 0.4529) / (1 - 0.4529)
                    r = int(21 * factor)
                    g = int(32 + (10 * factor))
                    b = int(30 + (10 * factor))
                canvas.setFillColorRGB(r / 255, g / 255, b / 255)
                y = height * i / steps
                canvas.rect(0, y, width, height / steps, fill=1, stroke=0)
        else:
            try:
                drawing = svg2rlg("staticfiles/reports/toc.svg")
                if drawing:
                    def apply_opacity(d, alpha):
                        for e in d.contents:
                            if hasattr(e, 'fillOpacity'):
                                e.fillOpacity = alpha
                            if hasattr(e, 'strokeOpacity'):
                                e.strokeOpacity = alpha
                            if hasattr(e, 'contents'):
                                apply_opacity(e, alpha)
                    apply_opacity(drawing, 0.1)
                    renderPDF.draw(drawing, canvas, x=0, y=0)
            except Exception as e:
                print("SVG load failed:", e)

            canvas.setFont(FONT_INTER_REGULAR, FONT_SIZE_MEDIUM)
            canvas.setFillColor(PMX_GREEN)
            text = "Thrive Limitless"
            text_width = stringWidth(text, FONT_INTER_REGULAR, FONT_SIZE_MEDIUM)
            canvas.drawString(A4[0] - 32 - text_width, A4[1] - 31, text)

        canvas.restoreState()

    def draw_footer(self, canvas, doc):
        if doc.page == 1:
            return

        canvas.saveState()
        logo_x, logo_y = 36, 22
        logo_width, logo_height = 81, 35.695
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
        if page_number <= 2:
            return
        text = f"Page {page_number:02d} - {total_pages:02d}"
        font = FONT_INTER_REGULAR
        size = FONT_SIZE_MEDIUM
        text_width = stringWidth(text, font, size)
        self.setFont(font, size)
        self.setFillColor(PMX_GREEN)
        self.drawString(A4[0] - 32 - text_width, 31, text)

class RoundedPill(Flowable):
    def __init__(
        self,
        text,
        bg_color,
        radius=9,
        width=64,
        height=18,
        font_size=8,
        text_color=colors.white,
        border_color=None,
        border_width=0.2,
        font_name=FONT_INTER_REGULAR,
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
        self.font_name=font_name

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.canv.saveState()

        # Fill background
        self.canv.setFillColor(self.bg_color)
        if self.border_color:
            self.canv.setStrokeColor(self.border_color)
            self.canv.setLineWidth(self.border_width)
            stroke_val = 1
        else:
            self.canv.setStrokeColor(self.bg_color)  # invisible stroke
            stroke_val = 0

        self.canv.roundRect(0, 0, self.width, self.height, self.radius, stroke=stroke_val, fill=1)

        # Text
        self.canv.setFont(self.font_name, self.font_size)
        self.canv.setFillColor(self.text_color)
        text_width = self.canv.stringWidth(self.text, self.font_name, self.font_size)
        center_x = self.width / 2
        center_y = (self.height - self.font_size) / 2 + 0.3 * self.font_size  # Better vertical alignment
        self.canv.drawCentredString(center_x, center_y, self.text)

        self.canv.restoreState()

class RoundedBox(Flowable):
    def __init__(self, width, height=None, content=None, corner_radius=8,border_radius=0.4,stroke_color=PMX_GREEN,fill_color=colors.white ):
        super().__init__()
        self.width = width
        self.height = height  # Optional: can be None for dynamic height
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

class GradientScoreBar:
    def __init__(
        self,
        width=478,
        height=6,
        score=102,
        data_min=80,
        data_max=120,
        units=None,
        label_text="Very Low",
        top_labels=None,
        bottom_labels_2=None,
        bottom_labels=None,
        gradient_colors=None,
        label_margin=15
    ):
        self.width = width
        self.height = height
        self.score = score
        self.data_min = data_min
        self.data_max = data_max
        self.label_text = label_text
        self.top_labels = top_labels or []
        self.bottom_labels = bottom_labels or []
        self.bottom_labels_2=bottom_labels_2 or []
        self.label_margin = label_margin
        self.units=units

        default_gradient = [
            (0.0, "#ED005F"),
            (0.351, "#F49E5C"),
            (0.7019, "#F4CE5C"),
            (1.0, "#488F31"),
        ]
        raw_gradient = gradient_colors or default_gradient
        self.gradient_colors = [(pos, self.hex_to_color(color)) for pos, color in raw_gradient]

    def hex_to_color(self, hex_code):
        hex_code = hex_code.lstrip("#")
        return Color(int(hex_code[0:2], 16) / 255.0,
                     int(hex_code[2:4], 16) / 255.0,
                     int(hex_code[4:6], 16) / 255.0)

    def interpolate_color(self, c1, c2, t):
        r = c1.red + (c2.red - c1.red) * t
        g = c1.green + (c2.green - c1.green) * t
        b = c1.blue + (c2.blue - c1.blue) * t
        return Color(r, g, b)

    def lighten_color(self, color, factor=0.4):
        return Color(
            color.red + (1.0 - color.red) * factor,
            color.green + (1.0 - color.green) * factor,
            color.blue + (1.0 - color.blue) * factor
        )

    def get_multicolor_gradient(self, t):
        for i in range(len(self.gradient_colors) - 1):
            if self.gradient_colors[i][0] <= t <= self.gradient_colors[i + 1][0]:
                t_local = (t - self.gradient_colors[i][0]) / (self.gradient_colors[i + 1][0] - self.gradient_colors[i][0])
                return self.interpolate_color(self.gradient_colors[i][1], self.gradient_colors[i + 1][1], t_local)
        return self.gradient_colors[-1][1]

    def draw(self):
        radius = 16
        pill_h = 20
        padding = 15
        label_font = FONT_INTER_REGULAR
        font_color = colors.HexColor("#667085")

        total_label_height = 0
        if self.top_labels:
            total_label_height += padding
        if self.bottom_labels:
            total_label_height += padding

        total_height = pill_h + self.height + total_label_height
        d = Drawing(self.width, total_height)

        if self.units:
            y = total_height - padding
            count = len(self.units)
            for i, text in enumerate(self.units):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                d.add(String(x, y, text, fontName=label_font, fontSize=9, fillColor=black))
        # Top labels
        if self.top_labels:
            if self.units==None:
                y = total_height - padding
            else:
                y = total_height 
            count = len(self.top_labels)
            for i, text in enumerate(self.top_labels):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                text_width = len(text) * 4.5

                if i == 0:
                    pass  # left align
                elif i == count - 1:
                    x -= text_width  # right align
                else:
                    x -= text_width / 2  # center align

                d.add(String(x, y, text, fontName=label_font, fontSize=7, fillColor=font_color))

        # Bar
        bar_y = total_height - self.height - (padding if self.top_labels else 0) - pill_h // 2
        d.add(Rect(0, bar_y, self.width, self.height, rx=radius, ry=radius, fillColor=white, strokeColor=None))

        # Gradient segments
        segments = 600
        for i in range(segments):
            t = i / (segments - 1)
            color = self.get_multicolor_gradient(t)
            x = t * self.width
            seg_width = self.width / segments
            d.add(Rect(x, bar_y, seg_width + 1, self.height, fillColor=color, strokeColor=None))

        # Bottom labels
        if self.bottom_labels:
            y = bar_y - padding
            count = len(self.bottom_labels)
            for i, text in enumerate(self.bottom_labels):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                text_width = len(text) * 4.5

                if i == 0:
                    pass  # left align
                elif i == count - 1:
                    x -= text_width  # right align
                else:
                    x -= text_width / 2  # center align

                d.add(String(x, y, text, fontName=label_font, fontSize=7, fillColor=font_color))
        if self.bottom_labels_2:
            if self.bottom_labels==None:
                y = bar_y - padding
            else:
                y = bar_y - padding -padding
            count = len(self.bottom_labels_2)
            for i, text in enumerate(self.bottom_labels_2):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                text_width = len(text) * 4.5

                if i == 0:
                    pass  # left align
                elif i == count - 1:
                    x -= text_width  # right align
                else:
                    x -= text_width / 2  # center align

                d.add(String(x, y, text, fontName=label_font, fontSize=7, fillColor=font_color))  

        # Score position clamping
        score_ratio = (self.score - self.data_min) / (self.data_max - self.data_min)
        clamped_ratio = min(max(score_ratio, 0), 1)
        score_color = self.get_multicolor_gradient(clamped_ratio)

        pill_w = 38
        score_x = clamped_ratio * self.width
        score_x = max(min(score_x, self.width - pill_w / 2), pill_w / 2)

        pill_y = bar_y + self.height / 2 - pill_h / 2
        score_fill = self.lighten_color(score_color)

        d.add(Rect(score_x - pill_w / 2, pill_y, pill_w, pill_h,
                   rx=pill_h / 2, ry=pill_h / 2,
                   fillColor=score_fill, strokeColor=score_color, strokeWidth=1))

        score_text = str(self.score)
        score_text_x = score_x - (len(score_text) * 5 / 2)
        d.add(String(score_text_x, pill_y + 6, score_text,
                     fontName=label_font, fontSize=10.435, fillColor=colors.HexColor("#003632")))

        return d, score_color

class ImageWithOverlayText(Flowable):
    def __init__(self, image_path, width, height, text_data, styles):
        super().__init__()
        self.width = width
        self.height = height
        self.text_data = text_data  # List of tuples: (text, x, y, style_name)
        self.image_stream = self.flatten_image_to_white(image_path)
        self.styles = getSampleStyleSheet()
        self.init_styles()

    def flatten_image_to_white(self, image_path):
        img = PILImage.open(image_path)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = PILImage.new("RGB", img.size, (255, 255, 255))  # White background
            bg.paste(img, mask=img.split()[-1])  # Use alpha as mask
        else:
            bg = img.convert("RGB")

        buffer = io.BytesIO()
        bg.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    def init_styles(self):
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

    def draw(self):
        img = ImageReader(self.image_stream)
        self.canv.drawImage(img, 0, 0, width=self.width, height=self.height)

        for text, x, y, style_name in self.text_data:
            val_unit = text.strip().split()

            if len(val_unit) == 2:
                val, unit = val_unit
                inline_text = (
                    f'<font name="{FONT_INTER_SEMI_BOLD}" color="{PMX_GREEN}" size="12">{val}</font> '
                    f'<font name="{FONT_INTER_REGULAR}" color="#667085" size="8">{unit}</font>'
                )
            else:
                val = val_unit[0]
                inline_text = (
                    f'<font name="{FONT_INTER_SEMI_BOLD}" color="{PMX_GREEN}" size="12">{val}</font>'
                )

            para = Paragraph(inline_text, self.styles[style_name])
            w, h = para.wrapOn(self.canv, self.width, self.height)
            para.drawOn(self.canv, x, y - h)



class ThriveRoadmapTemplate:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.base_path = Path("staticfiles/icons")
        self.init_styles()
        self.svg_dir = "staticfiles/icons/"

    def _get_logo(self):
        possible_paths = [
            self.base_path / "pmx_health.svg",
            "staticfiles/reports/pmx_health.svg",
            "staticfiles/icons/pmx_health.svg",
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
        self.styles.add(ParagraphStyle(
            name="MixedInlineStyle",
            fontName=FONT_RALEWAY_REGULAR,  # Fallback
            fontSize=75,
            leading=100, 
            textColor=colors.white,
            alignment=TA_LEFT,
            leftIndent=0,          
            firstLineIndent=0,

        )),
        self.styles.add(ParagraphStyle(
            name="MixedRalewayLine",
            fontName=FONT_RALEWAY_REGULAR,  # fallback
            fontSize=38.426,               
            textColor=colors.white,
            alignment=0,
            leading=48.033,
            leftIndent=0,          
            firstLineIndent=0,  
        )),
        self.styles.add(ParagraphStyle(
            "FrstPageHeader",
            fontName=FONT_RALEWAY_REGULAR,        
            fontSize=30,                  
            leading=38,                 
            textColor=colors.HexColor("#B3DEDA"),
            alignment=TA_LEFT
        )),
        self.styles.add(ParagraphStyle(
            "FrstPageTitle",
            fontName=FONT_INTER_REGULAR,         
            fontSize=20,                  
            leading=30,                
            textColor=colors.HexColor("#B3DEDA"),
            alignment=TA_LEFT           
        )),
        self.styles.add(ParagraphStyle(
            "TOCTitleStyle",
            fontName=FONT_RALEWAY_MEDIUM,
            fontSize=30,
            textColor=PMX_GREEN,
            leading=38,
            alignment=TA_LEFT,
        )),
        self.styles.add(ParagraphStyle(
            "TOCEntryText",
            fontName=FONT_INTER_REGULAR,
            fontSize=14,
            textColor=colors.HexColor("#002624"),
            leading=30,
            #alignment=TA_LEFT
        )),
        self.styles.add(ParagraphStyle(
            "toc_pagenum",
            fontName=FONT_INTER_REGULAR,                 
            fontSize=20,
            leading=30,                       
            textColor=PMX_GREEN,
            alignment=TA_RIGHT
        ))
        self.styles.add(ParagraphStyle(
            "profile_card_name",
            fontName=FONT_RALEWAY_MEDIUM,               # Ensure this font is registered properly
            fontSize=36,
            leading=44,                               # 122.222% of 36px
            textColor=PMX_GREEN,
        ))
        self.styles.add(ParagraphStyle(
            name="profile_card_otherstyles",
            fontName=FONT_INTER_REGULAR,               # Make sure Inter is registered
            fontSize=16,
            leading=24,                     # 150% line height
            textColor=PMX_GREEN,
        ))
        self.styles.add(ParagraphStyle(
            "box_title_style",
            fontName=FONT_RALEWAY_BOLD,
            fontSize=10,
            leading=10,
            textColor=PMX_GREEN,
            spaceAfter=0,
            spaceBefore=0
        )),
        self.styles.add(ParagraphStyle(
            "box_value_style",
            fontName=FONT_INTER_MEDIUM,  
            fontSize=14,
            leading=20,  
            textColor=colors.HexColor("#003632"),
            spaceAfter=0,
            spaceBefore=0
        )),
        self.styles.add(ParagraphStyle(
            "box_decimal_style",
            fontName=FONT_INTER_REGULAR,             
            fontSize=8,
            leading=18,                   
            textColor=colors.HexColor("#667085"),
            spaceAfter=0,
            spaceBefore=0
        )),
        self.styles.add(ParagraphStyle(
            "header_data_style",
            fontName=FONT_INTER_REGULAR,                   
            fontSize=12,
            leading=16,                         
            textColor=colors.HexColor("#667085"),
            spaceAfter=0,
            spaceBefore=0,
            alignment=0,                        
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
            "ear_screening_title",
            fontName=FONT_RALEWAY_SEMI_BOLD,  # Make sure this font is registered
            fontSize=12,
            leading=18,  # line height
            textColor=PMX_GREEN,
            spaceBefore=0,
            spaceAfter=0,
        ))
        self.styles.add(ParagraphStyle(
            "BrainScoreTitle",
            fontName=FONT_RALEWAY_SEMI_BOLD, 
            fontSize=18.936,
            leading=28.404,
            textColor=PMX_GREEN,
            spaceBefore=0,
            spaceAfter=0,
        ))
        self.styles.add(ParagraphStyle(
            "BrainScoreStyle",
            fontName=FONT_INTER_SEMI_BOLD,  
            fontSize=16,
            leading=24,
            textColor=colors.HexColor("#003632"),
            spaceBefore=0,
            spaceAfter=0,
        ))
        self.styles.add(ParagraphStyle(
            "BrainScoreRange",
            fontName=FONT_RALEWAY_SEMI_BOLD,  # You must register this font
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#344054"),
            spaceBefore=0,
            spaceAfter=0,
        ))
        self.styles.add(ParagraphStyle(
            "circle_fallback_style",
            fontName=FONT_INTER_REGULAR,  # built-in and supports Unicode
            fontSize=10,
            leading=10,
            textColor=PMX_GREEN,
            spaceAfter=0,
            spaceBefore=0,
            alignment=1,  
        ))
        self.styles.add(
            ParagraphStyle(
                "TableHeader",
                fontName=FONT_RALEWAY_BOLD,
                fontSize=12,
                textColor=PMX_GREEN,
                leading=14,
                alignment=TA_CENTER,
                spaceBefore=5,
                spaceAfter=3,
            ))
        self.styles.add(
            ParagraphStyle(
                "TableCell",
                fontName=FONT_INTER_REGULAR,
                fontSize=10,
                textColor=PMX_GREEN,
                leading=14,
                alignment=TA_LEFT,
                spaceBefore=0,
                spaceAfter=0,
            ))
        self.styles.add(ParagraphStyle(
            "homair",
            fontName=FONT_RALEWAY_MEDIUM,        # You must register this font first
            fontSize=30,
            leading=38,                # Equivalent to line-height
            textColor=PMX_GREEN,
            spaceAfter=0,
            spaceBefore=0
        ))
        self.styles.add(ParagraphStyle(
            'BulletStyle',
            fontSize=10,
            leading=16,
            leftIndent=0,
            bulletIndent=0,
            textColor=colors.HexColor("#667085"),
            spaceAfter=6
        ))
        self.styles.add(ParagraphStyle(
            name="AerobicStyle",
            fontName=FONT_RALEWAY_SEMI_BOLD,  # Make sure this font is registered
            fontSize=12,
            leading=18,  # Line height
            textColor=colors.HexColor("#000000"),
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
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        style = [
            # Headers
            ("BACKGROUND", (0, 0), (-1, 0), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, 0), PMX_GREEN),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            # ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), FONT_INTER_BOLD),
            ("FONTSIZE", (0, 0), (-1, 0), FONT_SIZE_MEDIUM),
            ("BOTTOMPADDING", (0, 0), (-1, 0), TABLE_HEADER_PADDING),
            ("TOPPADDING", (0, 0), (-1, 0), TABLE_HEADER_PADDING),
            # Data rows
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor('#00625B')),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),  # Number column
            ("ALIGN", (1, 1), (1, -1), "CENTER"),  # Medications column
            ("ALIGN", (2, 1), (2, -1), "CENTER"),  # Dosage column
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTNAME", (0, 1), (-1, -1), FONT_INTER_REGULAR),
            ("FONTSIZE", (0, 1), (-1, -1), FONT_SIZE_SMALL),
            ("TOPPADDING", (0, 1), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            ("RIGHTPADDING", (0, 0), (-1, -1), TABLE_PADDING),
            # Grid and Borders
            ("GRID", (0, 0), (-1, -1), 0.5, PMX_TABLE_GRID),
            ("LINEBELOW", (0, 0), (-1, 0), 0.01, colors.HexColor("#00625B")),
            ("LINEAFTER", (0, 0), (0, -1), 0.01, colors.HexColor("#00625B")),
            ("LINEAFTER", (1,0), (1, -1), 0.01, colors.HexColor("#00625B")),
            # Rounded Corners
            ("ROUNDEDCORNERS", [20, 20, 20, 20]),
            ("FONTNAME", (0, -1), (-1, -1), FONT_INTER_BOLD),
            ("BOX", (0, 0), (-1, -1), 0.01, colors.HexColor("#00625B"), None, None, "round"),
        ]

        # Add alternate row coloring starting from first data row (index 1)
        for i in range(2, len(table_data), 2):
            if i==len(table_data)-1:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#B3DEDA")))
            else:
                style.extend([("BACKGROUND", (0, i), (-1, i), PMX_TABLE_ALTERNATE_ROW),("TEXTCOLOR", (0, i), (0, i), colors.HexColor('#00625B')),("FONTNAME", (0, i), (-1, i), FONT_INTER_BOLD)])
                

        table.setStyle(TableStyle(style))
        return table

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

    def build_main_section(self, data):
        # --- 1. Icons and Graphics ---
        section=[]
        img_path_1 = os.path.join("staticfiles", "icons", "converted_pattern_2.png") 
        img_path_2 = os.path.join("staticfiles", "icons", "converted_pattern_3.png") 
        icon_path_pmx = os.path.join("staticfiles", "icons", "pmx_logo.svg")

        icon_pmx = self.svg_icon(icon_path_pmx, width=103, height=45.36)

        section.extend(self.add_bottom_left_image(img_path_1, x=-60, y=-765))
        section.extend(self.add_bottom_left_image(img_path_2, x=447, y=-133))

        # --- 2. Main Title ---
        main_title_1, main_title_2 = data.get("main_title", "Thrive limitless").split(" ")
        footer_link = data.get("footer_link", "www.pmxhealth.com")

        para = Paragraph(
            f'<span fontName="{FONT_RALEWAY_SEMI_BOLD}" fontSize="100" textColor="#FFFFFF">{main_title_1} </span>'
            f'<span fontName="{FONT_RALEWAY_REGULAR}" fontSize="40" textColor="#D0D5DD">{main_title_2.upper()}</span>',
            self.styles["MixedInlineStyle"]
        )

        main_sub_title_1, main_sub_title_2 = data.get("main_sub_title", "Longevity Roadmap").split(" ")
        para_1 = Paragraph(
            f'<font name={FONT_RALEWAY_BOLD} size="38" color="#FFFFFF">{main_sub_title_1}</font>'
            f'<font name={FONT_RALEWAY_REGULAR} size="38" color="#FFFFFF"> {main_sub_title_2}</font>',
            self.styles["MixedRalewayLine"]
        )

        # --- 3. Title Table ---
        table1 = Table([
            [icon_pmx],
            [para],
            [para_1]
        ])
        table2 = Table([[table1]], colWidths=[A4[0]])
        table2.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        # --- 4. Add to Story ---
        section.append(table2)
        section.append(Spacer(1, 32))
        section.append(FullPageWidthHRFlowable())
        section.append(Spacer(1, 40))
        section.append(self.get_welcome_table(data))
        section.append(Spacer(1, 40))
        section.append(FullPageWidthHRFlowable())
        return section
    
    def get_welcome_table(self, data: dict):
        name = data.get("user_profile_card", {}).get('name','')
        hello = data.get("hello", "Hello,")
        welcome_data = data.get(
            "welcome_data", 
            "Welcome to your longevity roadmap, This report has been carefully curated for you."
        )

        # Load and wrap the image
        img_path = os.path.join("staticfiles", "icons", "dp_face.png")        
        img = Image(img_path, width=100, height=100)
        img_cell = Table([[img]], colWidths=[100])
        img_cell.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        # Text block
        text_block = [
            Paragraph(hello, self.styles["FrstPageHeader"]),
            Spacer(1, 5),
            Paragraph(name, self.styles["FrstPageHeader"]),
            Spacer(1, 10),
            Paragraph(welcome_data, self.styles["FrstPageTitle"]),
        ]

        # Layout table: [ image | spacer | text ]
        layout_table = Table(
            [[img_cell, Spacer(1, 1), text_block]],
            colWidths=[100, 32, None],
            hAlign="LEFT"
        )
        layout_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        # Optional: wrap with outer margin
        container_table = Table([[layout_table]], colWidths=[A4[0]])
        container_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 40),
            ("RIGHTPADDING", (0, 0), (-1, -1), 40),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))

        return container_table

    def toc_table(self, toc_data: list) -> list:
        
        section=[]
        
        toc=Paragraph("Table Of Contents", self.styles["TOCTitleStyle"])

        toc_table_data = []
        table_bullet_path = os.path.join("staticfiles", "icons", "table_content_bullet.png")
        icon_bullet= Image(table_bullet_path, width=24, height=24)
        for item in toc_data:
            title=item.get("title","")
            page=item.get("page","")
            
            toc_table_data.append([
                icon_bullet,
                Spacer(1,13),
                Paragraph(title, self.styles["TOCEntryText"]),
                Paragraph(page, self.styles["toc_pagenum"]),
            ])

        toc_table = Table(toc_table_data,colWidths=[40,13,344,134])
        toc_table.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (0, -1), 8),
            ("BOTTOMPADDING", (0, 0), (0, -1), 8),
            ("LEFTPADDING", (0, 0), (0, -1), 8),
            ("RIGHTPADDING", (0, 0), (0, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (2, 0), (2, -1), "LEFT"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("TOPPADDING", (1, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (1, 0), (-1, -1), 4),
            ("LEFTPADDING", (1, 0), (-1, -1), 0),
            ("RIGHTPADDING", (1, 0), (-1, -1), 0),
        ]))
        toc_table2=Table([[toc],[Spacer(1, 8)],[toc_table]],colWidths=[A4[0]])
        toc_table2.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("ALIGN",(0,0),(-1,-1),"RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
        ]))
        section.append(toc_table2)
        return section

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
            "diet": "staticfiles/icons/food.svg"
        }

        widths_heights = {
            "id": {"width": 24, "height": 24},
            "gender": {"width": 16, "height": 16},
            "location": {"width": 16, "height": 16},
            "briefcase": {"width": 16, "height": 16},
            "dob_calendar": {"width": 16, "height": 16},
            "doa_calendar": {"width": 16, "height": 16},
            "diet": {"width": 16, "height": 24}
        }

        # Text values
        name = user_profile_card.get("name", "")
        user_id = user_profile_card.get("id", "")
        gender=user_profile_card.get("gender", "")
        if gender.lower()=="female":
            icon_paths["gender"]="staticfiles/icons/gender_female.svg"
        location = f"{user_profile_card.get('city', '')} - {user_profile_card.get('pincode', '')}"
        occupation = user_profile_card.get("occupation", "")
        dob = f"D.O.B - {user_profile_card.get('dob', '')}"
        doa = f"D.O.A - {user_profile_card.get('doa', '')}"
        diet = f"Dietary Preference - {user_profile_card.get('diet', '')}"

        style = self.styles["profile_card_otherstyles"]

        # Name row
        name_para = Paragraph(name, self.styles["profile_card_name"])

        # ID row
        id_row = self.icon_with_text(icon_paths["id"], f"ID - {user_id}", style,
                                    icon_width=widths_heights["id"]["width"], icon_height=widths_heights["id"]["height"])

        # Gender, Location, Occupation row
        gender_cell = self.icon_with_text(icon_paths["gender"], gender, style,
                                        icon_width=widths_heights["gender"]["width"], icon_height=widths_heights["gender"]["height"])
        location_cell = self.icon_with_text(icon_paths["location"], location, style,
                                            icon_width=widths_heights["location"]["width"], icon_height=widths_heights["location"]["height"])
        occupation_cell = self.icon_with_text(icon_paths["briefcase"], occupation, style,
                                            icon_width=widths_heights["briefcase"]["width"], icon_height=widths_heights["briefcase"]["height"])

        gender_width = self.get_dynamic_col_width(
            gender, 
            font_name=style.fontName, 
            font_size=style.fontSize, 
            icon_width=widths_heights["gender"]["width"]
        )

        location_width = self.get_dynamic_col_width(
            location, 
            font_name=style.fontName, 
            font_size=style.fontSize, 
            icon_width=widths_heights["location"]["width"]
        )

        occupation_width = self.get_dynamic_col_width(
            occupation, 
            font_name=style.fontName, 
            font_size=style.fontSize, 
            icon_width=widths_heights["briefcase"]["width"]
        )

        line2 = Table(
            [[gender_cell, location_cell, occupation_cell]],
            colWidths=[gender_width, location_width, occupation_width],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )

        # DOB, DOA row
        dob_cell = self.icon_with_text(icon_paths["dob_calendar"], dob, style,
                                    icon_width=widths_heights["dob_calendar"]["width"], icon_height=widths_heights["dob_calendar"]["height"])
        doa_cell = self.icon_with_text(icon_paths["doa_calendar"], doa, style,
                                    icon_width=widths_heights["doa_calendar"]["width"], icon_height=widths_heights["doa_calendar"]["height"])

        dob_width = self.get_dynamic_col_width(
            dob, font_name=style.fontName, font_size=style.fontSize, icon_width=widths_heights["dob_calendar"]["width"]
        )
        doa_width = self.get_dynamic_col_width(
            doa, font_name=style.fontName, font_size=style.fontSize, icon_width=widths_heights["doa_calendar"]["width"]
        )
        line3 = Table([[dob_cell, doa_cell]],
                    colWidths =[dob_width,doa_width],
                    style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)])

        # Diet row
        diet_cell = self.icon_with_text(icon_paths["diet"], diet, style,
                                        icon_width=widths_heights["diet"]["width"], icon_height=widths_heights["diet"]["height"])

        # Combine all text parts
        text_block = [
            [id_row],
            [name_para],
            [line2],
            [line3],
            [diet_cell],
            [Spacer(1,24)]
        ]

        text_table = Table(text_block, style=[
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])

        # Avatar Image
        avatar = Image(icon_paths["avatar"], width=100, height=100)
        avatar.hAlign = "LEFT"

        # Combine Avatar and Text in main layout
        final_table = Table(
            [[avatar,Spacer(1,32), text_table]],
            colWidths=[100, 32,None],
            style=[
                ("VALIGN", (1, 0), (1, -1), "TOP"),
                ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
        final_table2 = Table(
            [[final_table]],
            colWidths=[A4[0]],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 32),
                ("RIGHTPADDING", (0, 0), (-1, -1), 32),
                #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )
        return final_table2

    def get_health_metrics_left_column(self,profile_card_data,data):
        metrics=profile_card_data.get("metrics",[])
        icon_paths={
            "Vascular Age":"heart_rate.svg",
            "Heart Rate Variability":"calorie_2.svg",    
            "Grip Strength (Left)"  :"grip_strength.svg",  
            "Grip Strength (Right)" : "grip_strength.svg",
            "Cognitive"   :"Cognitive.svg"
        }
        section = []
        # for idx,metric in enumerate(metrics):
        #     # Top: title + pill
        #     title_para = Paragraph(metric['title'], self.styles["box_title_style"])
        #     pill_para = RoundedPill(metric["pill"], colors.HexColor(metric["pill_color"]), 8, 80, 18, 8, colors.HexColor("#EFEFEF"))

        #     top_stack = Table(
        #         [[title_para, pill_para]],
        #         colWidths=[106,80],
        #         style=[
        #             ("LEFTPADDING", (0, 0), (-1, -1), 0),
        #             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        #             ("TOPPADDING", (0, 0), (-1, -1), 0),
        #             ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        #             ("ALIGN", (0, 0), (0, 0), "LEFT"),
        #             ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        #             ("VALIGN", (0, 0), (-1, -1), "CENTER"),
        #         ]
        #     )

        #     # Bottom: merged major + minor value + footer
        #     value = metric['value']
        #     suff = metric.get('suff', '')

        #     # Inline-styled paragraph
        #     value_inline = Paragraph(value,self.styles["box_value_style"])
        #     suff_inline=Paragraph(suff,self.styles["box_decimal_style"])
        #     footer_para = Paragraph(metric["footer"], self.styles["box_decimal_style"]) if metric.get("footer") else Spacer(1, 0)
        #     suff_box = Table(
        #         [[suff_inline]],
        #         style=[
        #             ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
        #             ("LEFTPADDING", (0, 0), (0, 0), 0),
        #             ("RIGHTPADDING", (0, 0), (0, 0), 0),
        #             ("TOPPADDING", (0, 0), (0, 0), 0),
        #             ("BOTTOMPADDING", (0, 0), (0, 0), 0),
        #         ]
        #     )
        #     text_width = stringWidth(value, self.styles["box_value_style"].fontName, self.styles["box_value_style"].fontSize)
        #     bottom_stack = Table(
        #         [[value_inline, Spacer(1, 3), suff_box, footer_para]],
        #         colWidths=[text_width, 3, 12, None],
        #         style=[
        #             ("LEFTPADDING", (0, 0), (-1, -1), 0),
        #             ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        #             ("TOPPADDING", (0, 0), (-1, -1), 0),
        #             ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        #             ("ALIGN", (0, 0), (0, 0), "LEFT"),
        #             ("ALIGN", (2, 0), (2, 0), "LEFT"),
        #             ("VALIGN", (0, 0), (-1, -1), "CENTER"),
        #         ]
        #     )


        #     # Combine top and bottom into inner card
        #     inner_table = Table(
        #         [[top_stack], [bottom_stack]],
        #         colWidths=[192]
        #     )
        #     icon_path = os.path.join("staticfiles", "icons", icon_paths.get(metric['title'],""))

        #     icon = self.svg_icon(icon_path, width=24, height=24)

        #     total_table=Table([[icon,Spacer(0,8),inner_table]],colWidths=[24,8,192])
        #     total_table.setStyle(TableStyle([
        #         ("VALIGN",(0,0),(0,0),"MIDDLE"),
        #         ("ALIGN",(0,0),(-1,-1),"CENTER"),
        #         #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        #     ]))

        #     padded_inner = Table([[total_table]], colWidths=[250])
        #     padded_inner.setStyle(TableStyle([
        #         ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        #         ("LEFTPADDING", (0, 0), (-1, -1), 8),
        #         ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        #         ("TOPPADDING", (0, 0), (-1, -1), 6),
        #         ("BOTTOMPADDING", (0, 0), (-1, -1),6),
        #         #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        #     ]))

        #     rounded_card = RoundedBox(
        #         width=250,
        #         height=68,
        #         content=padded_inner,
        #         corner_radius=16,
        #         border_radius=0.4
        #     )

        #     section.append(rounded_card)
        #     if idx < len(metrics) - 1:
        #         section.append(Spacer(1, 16))
        
        # section=[]
        for idx,metric in enumerate(metrics):
            # Top: title + pill
            title_para = Paragraph(metric['title'], self.styles["box_title_style"])
            pill_para = RoundedPill(metric["pill"], colors.HexColor(metric["pill_color"]), 8, 80, 18, 8, colors.HexColor("#EFEFEF"))

            top_stack = Table(
                [[title_para, pill_para]],
                colWidths=[106,6,80],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )

            # Bottom: merged major + minor value + footer
            value = metric['value']
            suff = metric.get('suff', '')

            # Inline-styled paragraph
            value_inline = Paragraph(value,self.styles["box_value_style"])
            suff_inline=Paragraph(suff,self.styles["box_decimal_style"])
            if metric.get("footer"):
                footer_text = Paragraph(
                    f'<para alignment="right">{metric["footer"]}</para>',
                    self.styles["box_decimal_style"]
                )

                footer_stack = Table(
                    [[Spacer(1, 8)], [footer_text]],
                    colWidths=[192],  # Force full width to let right align take effect
                    style=[
                        ("VALIGN", (0, 1), (-1, -1), "BOTTOM"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )

            else:
                footer_stack = Spacer(1, 0)            
            suff_box = Table(
                [[Spacer(1, 4)], [suff_inline]],
                style=[
                    ("VALIGN", (0, 1), (-1, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )

            text_width = stringWidth(value, self.styles["box_value_style"].fontName, self.styles["box_value_style"].fontSize)
            suff_width = stringWidth(suff, self.styles["box_decimal_style"].fontName, self.styles["box_decimal_style"].fontSize)

            bottom_stack = Table(
                [[value_inline, Spacer(1, 3),suff_box , footer_stack]],
                colWidths =[text_width, 3, suff_width, 192 - (text_width + 9 + suff_width)],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "LEFT"),
                    ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("VALIGN", (2, 0), (2, -1), "BOTTOM"),
                ]
            )


            # Combine top and bottom into inner card
            inner_table = Table(
                [[top_stack], [bottom_stack]],
                colWidths=[192]
            )
            inner_table.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            icon_path = os.path.join("staticfiles", "icons", icon_paths.get(metric["title"],""))

            icon = self.svg_icon(icon_path, width=24, height=24)

            total_table=Table([[icon,Spacer(0,8),inner_table]],colWidths=[24,8,192])
            total_table.setStyle(TableStyle([
                ("VALIGN",(0,0),(0,0),"MIDDLE"),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            padded_inner = Table([[total_table]], colWidths=[250])
            padded_inner.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1),12),
            ]))

            rounded_card = RoundedBox(
                width=248,
                height=68,
                content=padded_inner,
                corner_radius=16,
                border_radius=0.4
            )

            section.append(rounded_card)
            if idx < len(metrics) - 1:
                section.append(Spacer(1, 16))

        section_table = Table([[section]])
        section_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            #("BOX", (0, 0), (-1, -1), 0.5, colors.black),

        ]))
        
        gender=data.get("gender","")
        if gender.lower()=="male":
            ahw_path = os.path.join("staticfiles", "icons", "male_age_ht_wt.png")
        else:
            ahw_path = os.path.join("staticfiles", "icons", "female_age_ht_wt.png")
        image_= Image(ahw_path, width=222, height=308)
        

        right_metric_table=Table([[image_]])
        right_metric_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 15),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 66),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 76),
            #("BOX", (0, 0), (-1, -1), 0.5, colors.black),

        ]))
        section_table2=Table([[section_table,right_metric_table]],colWidths=[309,A4[0]-309])
        section_table2.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 34),
            ("RIGHTPADDING", (0, 0), (-1, -1), 38.88),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            
            #("BOX", (0, 0), (-1, -1), 0.5, colors.black),

        ]))
        return section_table2

    def inner_rounded_table_data(self,symptoms,title,icon,width=A4[0]-64):    
        bullets = []
        title_para = Paragraph(title, self.styles["SvgBulletTitle"])

        bullets.append([
            icon,
            Spacer(1,10),
            title_para
        ])
        bullets.append([Spacer(1,16)])
        icon_path = os.path.join(svg_dir,"bullet.svg")  
        icon_bullet = self.svg_icon(icon_path, width=16, height=16)
        for i, item in enumerate(symptoms):
            bullets.append([
                icon_bullet,
                Spacer(1, 10),
                Paragraph(item, self.styles["bullet_after_text"]),
            ])
            if i != len(symptoms) - 1:  # Only add spacer if not the last item
                bullets.append([Spacer(1, 16)])

        if bullets:
            bullet_table = Table(bullets,colWidths=[16,10,width-16-16-16-10])
            
            bullet_table.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]))

            # Inner table with 16pt padding inside box
            inner_table = Table([[bullet_table]])
            inner_table.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ]))

            rounded_box = RoundedBox(
                width=width,
                height=None,
                content=inner_table,
                corner_radius=16,
                border_radius=0.1,
                fill_color=colors.white,
                stroke_color=colors.HexColor("#D9E9E6")
            )
            return rounded_box
        return None

    def get_current_symptoms_conditions(self,current_symptoms_conditions):

        section = []
        header=current_symptoms_conditions.get("header","")
        csc=Paragraph(header, self.styles["TOCTitleStyle"])
        section.append([csc])
        section.append([Spacer(1,8)])
        header_data=current_symptoms_conditions.get("header_data","")
        csc_data=Paragraph(header_data, self.styles["header_data_style"])
        section.append([csc_data])
        section.append([Spacer(1,40)])
        
        icon_path = os.path.join(svg_dir,"bullet_text_icon.svg")  
        icon = self.svg_icon(icon_path, width=24, height=24)
        # ---------- Bullet Points: Current Symptoms ----------
        symptoms = current_symptoms_conditions.get("symptoms_data", {}).get("title_data", [])
        title =  current_symptoms_conditions.get("symptoms_data", {}).get("title", "")
        section.append([self.inner_rounded_table_data(symptoms,title,icon)])
        section.append([Spacer(1, 8)])
        symptoms = current_symptoms_conditions.get("conditions_data", {}).get("title_data", [])
        title =  current_symptoms_conditions.get("conditions_data", {}).get("title", "")
        section.append([self.inner_rounded_table_data(symptoms,title,icon)])

        section_table = Table(section, colWidths=[A4[0]])
        section_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return section_table
    
    def get_your_current_stack(self,your_current_stack):

        section = []
        header=your_current_stack.get("header","")
        cs=Paragraph(header, self.styles["TOCTitleStyle"])
        section.append([cs])
        section.append([Spacer(1,8)])
        header_data=your_current_stack.get("header_data","")
        cs_data=Paragraph(header_data, self.styles["header_data_style"])
        section.append([cs_data])
        section.append([Spacer(1,32)])
        
        icon_path = os.path.join(svg_dir,"bullet_text_icon.svg")  
        icon = self.svg_icon(icon_path, width=24, height=24)
        # ---------- Bullet Points: Current Symptoms ----------
        medications = your_current_stack.get("medications", {}).get("title_data", [])
        title =  your_current_stack.get("medications", {}).get("title", "")
        section.append([self.inner_rounded_table_data(medications,title,icon)])
        section.append([Spacer(1, 8)])
        supplements = your_current_stack.get("supplements", {}).get("title_data", [])
        title =  your_current_stack.get("supplements", {}).get("title", "")
        section.append([self.inner_rounded_table_data(supplements,title,icon)])

        section_table = Table(section, colWidths=[A4[0]])
        section_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return section_table

    def get_family_past_histories(self, family_past_histories):
        section = []

        # 1. Header and Subheader
        header = family_past_histories.get("header", "")
        section.append([Paragraph(header, self.styles["TOCTitleStyle"])])
        section.append([Spacer(1, 8)])

        header_data = family_past_histories.get("header_data", "")
        section.append([Paragraph(header_data, self.styles["header_data_style"])])
        section.append([Spacer(1, 24)])

        # 2. Extract data
        title = family_past_histories.get("family_history", {}).get("title", "")
        mother_data = family_past_histories.get("family_history", {}).get("mother_side", {}).get("title_data", [])
        mother_title = family_past_histories.get("family_history", {}).get("mother_side", {}).get("title", "")
        father_data = family_past_histories.get("family_history", {}).get("father_side", {}).get("title_data", [])
        father_title = family_past_histories.get("family_history", {}).get("father_side", {}).get("title", "")

        # 3. Icons
        svg_dir = "staticfiles/icons/"
        icon_family = self.svg_icon(os.path.join(svg_dir, "family.svg"), width=24, height=24)
        icon_male = self.svg_icon(os.path.join(svg_dir, "gender_male.svg"), width=24, height=24)
        icon_female = self.svg_icon(os.path.join(svg_dir, "gender_female2.svg"), width=24, height=24)

        # 4. Inner Tables
        left_stack = self.inner_rounded_table_data(mother_data, mother_title, icon_female, width=246)
        right_stack = self.inner_rounded_table_data(father_data, father_title, icon_male, width=246)

        # 5. Total Stack (side-by-side)
        total_stack = Table([[left_stack,Spacer(1,8), right_stack]], colWidths=[246,8, 246])
        total_stack.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        # 6. Title row
        title_para = Paragraph(title, self.styles["SvgBulletTitle"])
        family_header_row = [icon_family, Spacer(1, 10), title_para]

        # 7. Combine Title Row and Total Stack into one table
        family_history_table = Table([
            family_header_row,
            [total_stack, '', '']  # fill empty cells for spanning
        ], colWidths=[24, 10, A4[0] - 64 - 34])  # match widths with padding considered

        family_history_table.setStyle(TableStyle([
            ("SPAN", (0, 1), (2, 1)),  # Span across all 3 columns in 2nd row
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))

        # 8. Wrap it in rounded box
        total_table = Table([[family_history_table]], colWidths=[A4[0] - 64])
        total_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))

        rounded_box = RoundedBox(
            width=A4[0] - 64,
            height=None,
            content=total_table,
            corner_radius=16,
            border_radius=0.4,
            fill_color=colors.white,
            stroke_color=colors.HexColor("#D9E9E6")
        )

        section.append([rounded_box])
        section.append([Spacer(1, 8)])

        # 9. Past History Section
        icon = self.svg_icon(os.path.join(svg_dir, "bullet_text_icon.svg"), width=24, height=24)
        symptoms = family_past_histories.get("past_history", {}).get("title_data", [])
        title = family_past_histories.get("past_history", {}).get("title", "")
        section.append([self.inner_rounded_table_data(symptoms, title, icon)])
        
        menstrual_history=family_past_histories.get("menstrual_history",{})
        if menstrual_history:
            section.append([Spacer(1, 8)])

            bullets = []
            title_para = Paragraph(menstrual_history.get("title",""), self.styles["SvgBulletTitle"])
            
            title_table=Table([
                [icon,
                Spacer(1, 10),
                title_para]
            ],colWidths=[24,10,None])
            bullets.append([title_table])

            icon_path = os.path.join(svg_dir, "bullet.svg")  
            icon_bullet = self.svg_icon(icon_path, width=16, height=16)

            bullets_ = []
            
            for i, item in enumerate(menstrual_history.get("title_data","")):
                bullets_.extend([
                    icon_bullet,
                    Spacer(1, 10),
                    Paragraph(item, self.styles["bullet_after_text"]),
                ])
                if i != len(symptoms) - 1:
                    bullets_.extend([Spacer(1, 8)])  # flat spacer for horizontal space between items

            if bullets_:
                # Wrap the extended list into a single table row (horizontal layout)
                bullet_table = Table([bullets_],colWidths=[16,10,130,8,16,10,164,8,16,10,112])  # List inside a list = single row
                bullet_table.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ]))
                # Inner table with padding around the content
                inner_table = Table([[bullet_table]])
                inner_table.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 16),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                    ("TOPPADDING", (0, 0), (-1, -1), 16),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                ]))
                bullets.append([inner_table])
                bullets_table=Table(bullets)
                rounded_box = RoundedBox(
                    width=A4[0] - 64,
                    height=None,
                    content=bullets_table,
                    corner_radius=16,
                    border_radius=0.1,
                    fill_color=colors.white,
                    stroke_color=colors.HexColor("#D9E9E6")
                )

                section.append([rounded_box])
        
        # 10. Wrap all in final section table
        section_table = Table(section, colWidths=[A4[0]])
        section_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return section_table

    def get_health_goals(self,health_goals_data):
        section = []
        header=health_goals_data.get("header","")
        cs=Paragraph(header, self.styles["TOCTitleStyle"])
        section.append([cs])
        section.append([Spacer(1,8)])
        header_data=health_goals_data.get("header_data","")
        cs_data=Paragraph(header_data, self.styles["header_data_style"])
        section.append([cs_data])
        section.append([Spacer(1,40)])
        
        icon_path = os.path.join(svg_dir,"bullet_text_icon.svg")  
        icon = self.svg_icon(icon_path, width=24, height=24)
        # ---------- Bullet Points: Current Symptoms ----------
        goals_data = health_goals_data.get("goals_data", [])
        title =  health_goals_data.get("title", "")
        section.append([self.inner_rounded_table_data(goals_data,title,icon)])

        section_table = Table(section, colWidths=[A4[0]])
        section_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return section_table

    def get_eye_screening_card(self, eye_data: dict, icon_paths: dict) -> Flowable:
    
        title = eye_data.get("title", "Eye Screening")
        below_data = eye_data.get("below_data", "")

        left_eye_score = eye_data.get("left_eye").get("left_eye_score", "")
        left_eye_color = eye_data.get("left_eye").get("left_eye_score_color", "")
        left_eye_title = eye_data.get("left_eye").get("title", "")

        right_eye_score = eye_data.get("right_eye").get("right_eye_score", "")
        right_eye_color = eye_data.get("right_eye").get("right_eye_score_color", "")
        right_eye_title = eye_data.get("right_eye").get("title", "")

        # Load icon
        icon_info = icon_paths.get(title, {})
        icon_path = os.path.join(svg_dir, icon_info.get("path", ""))
        icon = self.svg_icon(icon_path, width=icon_info.get("width", 20), height=icon_info.get("height", 20))

        # Title and description
        title_para = Paragraph(title, self.styles["box_title_style"])
        desc_para = Paragraph(below_data, self.styles["eye_screening_desc_style"])

        # Eye score title and pills
        left_title = Paragraph(left_eye_title, self.styles["box_title_style"])
        right_title = Paragraph(right_eye_title, self.styles["box_title_style"])

        left_pill = RoundedPill(left_eye_score, colors.HexColor(left_eye_color), 8, 80, 18, 8)
        right_pill = RoundedPill(right_eye_score, colors.HexColor(right_eye_color), 8, 80, 18, 8)

        # Scores table
        score_table = Table(
            [[left_title, right_title], [left_pill, right_pill]],
            colWidths=[217.5, 217.5],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ]
        )

        # Left column content
        left_stack = Table(
            [[title_para],[Spacer(1,3)] ,[desc_para], [Spacer(1, 8)], [score_table]],
            style=[
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1,-1), 0),
                ("LINEBELOW", (0, 3), (-1, 3), 0.01, colors.HexColor("#00625B")),
                #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ],
            colWidths=[467]
        )

        # Combine icon and left stack
        inner_table = Table(
            [[icon,Spacer(1,8), left_stack]],
            colWidths=[24,8, 467],
            style=[
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                #("BOX", (0, 0), (-1, -1), 0.5, colors.black),

            ]
        )

        rounded_box = RoundedBox(
            width=A4[0]-64,
            height=None,
            content=inner_table,
            corner_radius=16,
        )
        return rounded_box

    def get_vital_params(self, vital_params_data: dict):
        
        section_ = []
        header=vital_params_data.get("header","")
        cs=Paragraph(header, self.styles["TOCTitleStyle"])
        section_.append(cs)
        section_.append(Spacer(1,8))
        header_data=vital_params_data.get("header_data","")
        cs_data=Paragraph(header_data, self.styles["header_data_style"])
        section_.append(cs_data)
        section_.append(Spacer(1,32))

        title=vital_params_data.get("metrics","").get("title","")
        icon_path=os.path.join(svg_dir,"lifestyle.svg")


        icon_lifestyle = self.svg_icon(icon_path, width=24, height=24)
        title_para = Paragraph(title, self.styles["SvgBulletTitle"])
        family_header_row = [icon_lifestyle, Spacer(1, 10), title_para]

        section_.append(
            Table(
                [family_header_row],
                colWidths=[24, 10, A4[0]-24-10-64],
                style=[
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
                ],
            )
        )
        section_.append(Spacer(1, 14))

        # ---------- Vital Parameters ----------

        icon_paths={
            "Body Temperature":{
                "path":"temperature.svg",
                "width":9,
                "height":18
            },
            "Blood Oxygen":{
                "path":"blood_oxygen.svg",    
                "width":11.88,
                "height":18
            },
            "Blood Pressure (Left Arm)"  :{
                "path":"left.svg",
                "width":24,
                "height":24
            },
            "Blood Pressure (Right Arm)" : {
                "path":"right.svg",
                "width":24,
                "height":24
            },
            "Heart Rate"   :{
                "path":"HRV.svg",
                "width":24,
                "height":24
            },
            "Respiratory Rate"   :{
                "path":"respiratory_rate.svg",
                "width":17.02,
                "height":18
            },
            "Eye Screening"   :{
                "path":"HRV.svg",
                "width":24,
                "height":24
            }
        }
        metrics=vital_params_data.get("metrics",{}).get("metrics_data",[])

        section=[]
        for idx,metric in enumerate(metrics):
            # Top: title + pill
            title_para = Paragraph(metric['title'], self.styles["box_title_style"])
            pill_para = RoundedPill(metric["pill"], colors.HexColor(metric["pill_color"]), 8, 80, 18, 8, colors.HexColor("#EFEFEF"))

            top_stack = Table(
                [[title_para, pill_para]],
                colWidths=[106,6,80],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )

            # Bottom: merged major + minor value + footer
            value = metric['value']
            suff = metric.get('suff', '')

            # Inline-styled paragraph
            value_inline = Paragraph(value,self.styles["box_value_style"])
            suff_inline=Paragraph(suff,self.styles["box_decimal_style"])
            if metric.get("footer"):
                footer_text = Paragraph(
                    f'<para alignment="right">{metric["footer"]}</para>',
                    self.styles["box_decimal_style"]
                )

                footer_stack = Table(
                    [[Spacer(1, 8)], [footer_text]],
                    colWidths=[192],  # Force full width to let right align take effect
                    style=[
                        ("VALIGN", (0, 1), (-1, -1), "BOTTOM"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )

            else:
                footer_stack = Spacer(1, 0)            
            suff_box = Table(
                [[Spacer(1, 4)], [suff_inline]],
                style=[
                    ("VALIGN", (0, 1), (-1, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )

            text_width = stringWidth(value, self.styles["box_value_style"].fontName, self.styles["box_value_style"].fontSize)
            suff_width = stringWidth(suff, self.styles["box_decimal_style"].fontName, self.styles["box_decimal_style"].fontSize)

            bottom_stack = Table(
                [[value_inline, Spacer(1, 3),suff_box , footer_stack]],
                colWidths =[text_width, 3, suff_width, 192 - (text_width + 9 + suff_width)],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "LEFT"),
                    ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("VALIGN", (2, 0), (2, -1), "BOTTOM"),
                ]
            )


            # Combine top and bottom into inner card
            inner_table = Table(
                [[top_stack], [bottom_stack]],
                colWidths=[192]
            )
            inner_table.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            icon_path = os.path.join("staticfiles", "icons", icon_paths.get(metric['title'],"").get("path",""))

            icon = self.svg_icon(icon_path, width=icon_paths.get(metric['title'],"").get("width",""), height=icon_paths.get(metric['title'],"").get("height",""))

            total_table=Table([[icon,Spacer(0,8),inner_table]],colWidths=[24,8,192])
            total_table.setStyle(TableStyle([
                ("VALIGN",(0,0),(0,0),"MIDDLE"),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            padded_inner = Table([[total_table]], colWidths=[250])
            padded_inner.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1),12),
            ]))

            rounded_card = RoundedBox(
                width=248,
                height=68,
                content=padded_inner,
                corner_radius=16,
                border_radius=0.4
            )

            section.append(rounded_card)
        rows = []
        for i in range(0, len(section), 2):
            row = section[i:i+2]
            if len(row) < 2:
                row.append(Spacer(1, 15))  # Add spacer to the row (not section!)
            rows.append(row)
            rows.append([Spacer(1, 11)])

        eye_screening=vital_params_data.get("metrics",{}).get("eye_screening",[])


        section_table = Table(rows)
        section_table.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            #("BOX", (0, 0), (-1, -1), 0.5, colors.black),

        ]))
        section_.append(section_table)
        section_.append(self.get_eye_screening_card(eye_screening,icon_paths))
        final_table = Table([[item] for item in section_], colWidths=[A4[0]])

        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return final_table

    def ear_card(self, title, val,color="#488F31"):
        content = Table(
            [[Paragraph(title, self.styles["ear_screening_title"]),
            RoundedPill(val,color, 6, 121.5, 24)]],
            colWidths=[84.5, 121.5]
        )
        content.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            #("BOX",(0,0),(-1,-1),0.5,colors.black)
        ]))
        return RoundedBox(width=221.5, height=40, content=content, corner_radius=8,border_radius=0.1)
    
    def examination_card(self, ear_data, label="Left Ear"):
        rows = [
            [Paragraph(label, self.styles["ear_screening_title"])],
            # [""],  # Line separator
        ]
        for item in ear_data.get("data", [])[:3]:
            rows.append([Paragraph(item.get("name", ""), self.styles["ear_screening_title"])])
            rows.append([Paragraph(f"• {item.get('val', '')}", self.styles["eye_screening_desc_style"])])

        content_ = Table(rows, colWidths=[163])
        content_.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.1, colors.HexColor("#00625B")),
        ]))

        wrapper = Table([[content_]], colWidths=[163])
        wrapper.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))

        return RoundedBox(width=194.5, height=None, content=wrapper, corner_radius=16,border_radius=0.1)

    def get_ear_screening(self, ear_screening_data: dict):
        section_ = []
        header=ear_screening_data.get("header","")
        cs=Paragraph(header, self.styles["TOCTitleStyle"])
        section_.append(cs)
        section_.append(Spacer(1,8))
        header_data=ear_screening_data.get("header_data","")
        cs_data=Paragraph(header_data, self.styles["header_data_style"])
        section_.append(cs_data)
        section_.append(Spacer(1,32))


        # ---------- Vital Parameters ----------
    
        icon_path = os.path.join(svg_dir, "ear.svg")
        icon = self.svg_icon(icon_path, width=12, height=18)

        title_para = Paragraph(ear_screening_data['title'], self.styles["ear_screening_title"])
        value_para_ = Paragraph(ear_screening_data["title_data"], self.styles["eye_screening_desc_style"])
        left_stack_rows = [[title_para],[value_para_], [Spacer(1, 8)]]

        ear_screening_list = ear_screening_data.get("ear_screening_list", {})
        for item in ear_screening_list:
            header = item.get("header", "")
            left_ear = item.get("left_ear", {})
            right_ear = item.get("right_ear", {})
            bullet = self.svg_icon(os.path.join(svg_dir, "bullet.svg"), width=16, height=16)
            title__=Paragraph(header, self.styles["ear_screening_title"])
            value_para = Paragraph(item.get("header_data", ""), self.styles["eye_screening_desc_style"])

            if header == "Examination":
                left_card = self.examination_card(left_ear, label="Left Ear")
                right_card = self.examination_card(right_ear, label="Right Ear")
            else:
                left_card = self.ear_card(left_ear.get("name", "Left Ear"), left_ear.get("val", "Clear"),left_ear.get("color", ""))
                right_card = self.ear_card(right_ear.get("name", "Right Ear"), right_ear.get("val", "Clear"),right_ear.get("color", ""))

            left_right = Table([[left_card, Spacer(8, 1), right_card]], colWidths=[221.5, 8, 221.5])
            left_right.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            inner_table_2 = Table([[value_para]])
            inner_table_2.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            entry_table = Table([[title__], [inner_table_2],[Spacer(1,8)] ,[left_right]])
            entry_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            
            entry_table_ = Table([[bullet,Spacer(8,1),entry_table]],colWidths=[16,8,None])
            entry_table_.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))

            left_stack_rows.append([entry_table_])

        left_stack = Table(left_stack_rows)
        left_stack.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1),0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        inner_table = Table([[icon,Spacer(8,1) ,left_stack]],colWidths=[12,8,None])
        inner_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            #("BOX",(0,0),(-1,-1),0.5,colors.black)
        ]))

        rows_table = Table([[inner_table]])
        rows_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1),16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            #("BOX",(0,0),(-1,-1),0.5,colors.black)
        ]))

        section_.append(RoundedBox(width=A4[0]-64, height=None, content=rows_table, corner_radius=16))

        final_table = Table([[item] for item in section_], colWidths=[A4[0]])

        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        return final_table
    
    def get_brain_function_screen(self, brain_function_score: dict):
        section_ = []
        
        # Header Section
        header = brain_function_score.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section_.append(cs)
        section_.append(Spacer(1, 16))

        header_data = brain_function_score.get("header_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section_.append(cs_data)
        section_.append(Spacer(1, 32))

        # Icon and Data
        icon_path = os.path.join(svg_dir, "Cognitive.svg")
        icon = self.svg_icon(icon_path, width=24, height=24)

        brain_score = brain_function_score.get("brain_score_data", [])
        title_text = brain_function_score.get("title", "")
        score_text = brain_function_score.get("score", "")
        range_color = brain_function_score.get("color", "#000000")
        range_text = brain_function_score.get("range", "")
        gradient_colors=brain_function_score.get("gradient_colors", "")
        min_score=brain_function_score.get("min_score", "")
        max_score=brain_function_score.get("max_score", "")
        bottom_labels = brain_function_score.get("bottom_labels", "")


        # Paragraphs
        title_para = Paragraph(title_text, self.styles["BrainScoreTitle"])
        score_para = Paragraph(score_text, self.styles["BrainScoreStyle"])
        circle_para = Paragraph(f'<font color="{range_color}">&#9679;</font>', self.styles["circle_fallback_style"])
        # circle_para = Paragraph(circle_html, self.styles["box_title_style"])
        range_para = Paragraph(range_text, self.styles["BrainScoreRange"])

        # Widths for accurate layout
        title_width = stringWidth(title_text, self.styles["BrainScoreTitle"].fontName, self.styles["BrainScoreTitle"].fontSize)
        score_width = stringWidth(score_text, self.styles["BrainScoreStyle"].fontName, self.styles["BrainScoreStyle"].fontSize)
        range_width = stringWidth(range_text, self.styles["BrainScoreRange"].fontName, self.styles["BrainScoreRange"].fontSize)

        # Brain Score Table
        row_items = [icon, Spacer(1, 6), title_para, Spacer(1, 12), score_para, Spacer(1, 6), circle_para, Spacer(1, 6), range_para,""]
        col_widths = [24, 6, title_width, 12, score_width, 6, 6, 6, range_width,None]

        brain_score_table = Table([row_items], colWidths=col_widths)
        brain_score_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LINEBELOW", (0, 0), (-1, 0), 0.3, colors.HexColor("#00625B"))
        ]))
        full_brain_score_table = Table([[brain_score_table]], colWidths=[478])

        draw_list = [full_brain_score_table]

        # Body Cards with Gradient Bar
        for idx, item in enumerate(brain_score):
            title = item.get("title", "")
            title_data = item.get("title_data", "")
            score = item.get("score", 0)

            title_ = Paragraph(title, self.styles["ear_screening_title"])
            title_data_para = Paragraph(title_data, self.styles["eye_screening_desc_style"])

            drawing, color__ = GradientScoreBar(score=int(score), data_min=min_score, data_max=max_score,
                                                bottom_labels=bottom_labels,
                                                gradient_colors=gradient_colors).draw()

            def color_to_hex(color):
                r = int(color.red * 255)
                g = int(color.green * 255)
                b = int(color.blue * 255)
                return '#{:02X}{:02X}{:02X}'.format(r, g, b)

            hex_color = color_to_hex(color__)

            desc_block = Table([
                [title_],
                [Spacer(1, 2)],
                [title_data_para]
            ], colWidths=[478], rowHeights=[None, 2, None])

            card = Table([
                [desc_block, RoundedPill('low', hex_color, 8, 80, 18, 8, colors.HexColor('#EFEFEF'))]
            ], colWidths=[390, 88])
            card.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            content = Table([
                [card],
                [drawing]
            ], colWidths=[478])
            content.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            wrapper = Table([[content]], colWidths=[478])
            # if idx != len(brain_score) - 1:
            #     wrapper.setStyle(TableStyle([
            #         ("LINEBELOW", (0, 0), (-1, 0), 0.01, colors.HexColor("#00625B"))
            #     ]))

            draw_list.append(wrapper)

        # Outer Wrapper Box
        drawlist_table = Table([[draw_list]], colWidths=[478])
        drawlist_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, 0), 16),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
        ]))

        rounded_container = RoundedBox(width=A4[0] - 85, height=None, content=drawlist_table, corner_radius=12)
        section_.append(rounded_container)

        final_table = Table([[item] for item in section_], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

    def get_body_mass_index(self,bmi_data: dict,data):
        section_ = []
        # Header Section
        header = bmi_data.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section_.append(cs)
        section_.append(Spacer(1, 16))

        header_data = bmi_data.get("header_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section_.append(cs_data)
        section_.append(Spacer(1, 32))

        
        icon_path = os.path.join(self.svg_dir,"BMI.svg")  
        icon = self.svg_icon(icon_path, width=24, height=24)
        # ---------- Bullet Points: Current Symptoms ----------
        
        title=bmi_data.get("title","")
        title_data=bmi_data.get("title_data","")
        title_data_text = Paragraph(title_data, self.styles["eye_screening_desc_style"])        
        title_para = Paragraph(title, self.styles["SvgBulletTitle"])

        title_data= Table([
            [title_para],
            [title_data_text]
            ], colWidths=[445])
        title_data.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        svg_heading_row = Table([[icon,Spacer(1,8), title_data]], colWidths=[24,8,445])
        svg_heading_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("VALIGN", (0, 0), (0, 0), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        svg_dir = "staticfiles/icons/"
        if data.get("gender").lower()=="male":
            icon_path = os.path.join(svg_dir,'bmi_malee.png')
        elif data.get("gender").lower()=="female":
            icon_path = os.path.join(svg_dir,'bmi_femalee.png')
        # icon_bmi=Image(icon_path, width=271, height=326)
        
        Height=bmi_data.get("Height","00 cms")
        Waist=bmi_data.get("Waist","00 inch")
        Hip=bmi_data.get("Hip","00 inch")
        weight=bmi_data.get("weight","00 kg")
        WTH_Ratio=bmi_data.get("WTH_Ratio","00")
        gradient_colors=bmi_data.get("gradient_colors",[])
        min_val=bmi_data.get("min_val","")
        max_val=bmi_data.get("max_val","")
        top_labels=bmi_data.get("top_labels",[])
        bottom_labels=bmi_data.get("bottom_labels",[])

        text_data = [
            (Height, 95, 300, "ear_screening_title"),       # Height
            (Waist, 6, 175, "ear_screening_title"),        # Waist
            (Hip, 10, 120, "ear_screening_title"),        # Hip
            (WTH_Ratio, 228, 150, "ear_screening_title"),          # Waist to Hip Ratio
            (weight, 92, 5, "ear_screening_title"),        # Weight
        ]

        icon_bmi = ImageWithOverlayText(
            image_path=icon_path,
            width=271,
            height=326,
            text_data=text_data,
            styles=self.styles["ear_screening_title"]
        )
        drawing,color__ = GradientScoreBar(
                score=float(weight.split(" ")[0]),
                data_min=min_val,
                data_max=max_val,
                top_labels=top_labels,
                bottom_labels=bottom_labels,
                gradient_colors=gradient_colors
            ).draw()
        icon_row=Table([[icon_bmi]], colWidths=[271],rowHeights=[None])
        icon_row.setStyle(TableStyle([

            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 103),
            ("RIGHTPADDING", (0, 0), (-1, -1), 103),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        bmi_row_=Table([
            [svg_heading_row],
            [icon_row],
            [Spacer(1,8)],
            [drawing]
        ], colWidths=[477])
        bmi_row_.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        bmi_row=Table([
            [bmi_row_]
        ], colWidths=[A4[0]-86])
        bmi_row.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            #("BOX",(0,0),(-1,-1),0.3,colors.black)
        ]))
        
        rounded_box=RoundedBox(width=A4[0]-86, height=None, content=bmi_row, corner_radius=12)

        section_.append(rounded_box)        
        final_table = Table([[item] for item in section_], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("LEFTPADDING", (0, -1), (-1, -1), 43),
            ("RIGHTPADDING", (0, -1), (-1, -1), 43),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

    def get_body_composition(self, data: dict):

        body_composition = data.get("body_composition", {})
        title = body_composition.get("title", "")
        section=[]
        # ---------- Heading ----------
        heading = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(heading)
        section.append(Spacer(1, 2))

        # ---------- Icon and Title Data ----------
        icon_path = os.path.join(svg_dir, "BMI.svg")
        icon = self.svg_icon(icon_path, width=24, height=24)

        title_data = body_composition.get("title_data", "")
        title_data_text = Paragraph(title_data, self.styles["profile_card_otherstyles"])

        icon_path_bmi = os.path.join(svg_dir, "diagnosis_image.svg")
        icon_bmi = self.svg_icon(icon_path_bmi, width=250, height=294)


        image_data_val = Paragraph(
            "<para align='center'><font color='#26968D'>Image is not for diagnosis</font></para>",
            self.styles["box_decimal_style"]  # Or self.styles["decimal_style_"] if defined
        )
        body_weight = Paragraph(
            f'<para align="right">'
            f'<font name="{self.styles["box_decimal_style"].fontName}" size="{self.styles["box_decimal_style"].fontSize}"><b>56</b></font> '
            f'<font name="{self.styles["box_decimal_style"].fontName}" size="{self.styles["box_decimal_style"].fontSize}">kg</font>'
            f'</para>',
            self.styles["box_decimal_style"]
        )

        body_weight_title = Paragraph(
            '<para align="center"><font color="#00625B">Body Weight</font></para>',
            self.styles["box_decimal_style"]
        )

        body_weight_row = Table([
                [body_weight_title, body_weight]
            ],
            colWidths=[150, 100],  # Adjust widths as needed
        )
        body_weight_row.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ])
        )
        body_weight_row=RoundedBox(width=250, height=44, content=body_weight_row, corner_radius=16)
        svg_heading_row = Table(
            [
                [icon, "", title_data_text],
                [icon_bmi,"",""],
                [image_data_val, "", ""],
                [""],
                [body_weight_row,"",""],
                [""]  # placeholder cells to match column count
            ],
            colWidths=[28, 4, 218],
            rowHeights=[None, None,25,None,None,50]
        )

        # Set table style with a span across the second row (0,1) to (2,1)
        svg_heading_row.setStyle(TableStyle([
            ("SPAN", (0, 1), (2, 1)),
            ("SPAN", (0, 2), (2, 2)),
            ("SPAN", (0, 3), (2, 3)),          # Span full width on second row
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        # ---------- Body Composition Metrics ----------
        metrics = body_composition.get("metrics", "") 

        story = []
        for metric in metrics:
            # Top: title + pill
            title_para = Paragraph(f"<b>{metric['title']}</b>", self.styles["box_title_style"])
            pill_para = RoundedPill(metric["pill"], colors.HexColor(metric["pill_color"]), 8, 80, 18, 8, colors.HexColor("#EFEFEF"))

            top_stack = Table(
                [[title_para, pill_para]],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )

            # Bottom: merged major + minor value + footer
            value = metric['value']
            suff = metric.get('suff', '')

            # Inline-styled paragraph
            value_inline = Paragraph(
                f'<font name="{self.styles["box_value_style"].fontName}" size="{self.styles["box_value_style"].fontSize}"><b>{value}</b></font>'
                f'<font name="{self.styles["box_decimal_style"].fontName}" size="{self.styles["box_decimal_style"].fontSize}">{suff}</font>',
                self.styles["box_value_style"]
            )

            footer_para = Paragraph(metric["footer"], self.styles["box_decimal_style"]) if metric.get("footer") else Spacer(1, 0)

            bottom_stack = Table(
                [[value_inline, footer_para]],
                colWidths=[None, None],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
                ]
            )

            # Combine top and bottom into inner card
            inner_table = Table(
                [[top_stack], [bottom_stack]],
                colWidths=[194]
            )

            padded_inner = Table([[inner_table]], colWidths=[194])
            padded_inner.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]))

            rounded_card = RoundedBox(
                width=230.8,
                height=68.8,
                content=padded_inner,
                corner_radius=12
            )

            story.append(rounded_card)
            story.append(Spacer(1, 4))

        # Final layout with left icon and right cards
        body_comp_row = Table([[svg_heading_row, Spacer(1,38),story]], colWidths=[262,38, 230], rowHeights=[None])
        body_comp_row.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP")
        ]))
        section.append(body_comp_row)
        tscore_val=body_composition.get("tscore_val","")

        gradient_colors = [
                (0.0, "#488F31"),
                (0.35, "#F4CE5C"),
                (0.70, "#F49E5C"),
                (1.0, "#ED005F")
            ]
        drawing,color__ = GradientScoreBar(
                score=tscore_val,
                width=513,
                data_min=0.78,
                data_max=1.34,
                units=["BMD (g/cm2)",""],
                top_labels=["0.78","0.86","0.94", "1.02", "1.10", "1.18","1.26","1.34"],
                bottom_labels=["Osteoporosis","Osteopenia", "Normal"],
                bottom_labels_2=["-5","-4", "-3", "-2", "-1", "0","1","2","3"],
                gradient_colors=gradient_colors
            ).draw()


        tscore_title=body_composition.get("tscore","")
        tscore_data=body_composition.get("tscore_data","")
        
        title_=Paragraph(tscore_title, self.styles["profile_card_otherstyles"])
        title_data=Paragraph(tscore_data, self.styles["box_decimal_style"])
        
        rows = [
            [title_],
            [""],
            [title_data],
            [""],
            [drawing]
        ]
        content_ = Table(rows, colWidths=[529],rowHeights=[None, 8, None,8,None])
        
    
        content_.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            
        ]))

    
        section.append(content_)
        return section

    def get_fitness_assesment(self, fitness_assesment_data: dict):
        section_ = []
        # Header Section
        header = fitness_assesment_data.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section_.append(cs)
        section_.append(Spacer(1, 8))

        header_data = fitness_assesment_data.get("header_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section_.append(cs_data)
        section_.append(Spacer(1, 24))


        # ---------- Fitness Table ----------
        fitness_table_data = fitness_assesment_data.get("fitness_table_data", [])
        headers = [
            Paragraph(h, self.styles["TableHeader"])
            for h in [
                "Test Name",
                "Your Score",
                "Optimal Score"
            ]
        ]
        table_data = [headers]

        for ftd in fitness_table_data:
            test_name = ftd.get("test_name", "")
            your_score = ftd.get("your_score", "")
            optimal_score = ftd.get("optimal_score", "")

            your_score_pill = RoundedPill(your_score, colors.HexColor("#E6F4F3"), 8, 40, 18, 8, "#003632","#17B26A",0.2,FONT_INTER_BOLD)
            optimal_score_pill = RoundedPill(optimal_score, colors.HexColor("#E6F4F3"), 8, 40, 18, 8, "#003632","#17B26A",0.2,FONT_INTER_BOLD)

            row = [
                Paragraph(test_name, self.styles["TableCell"]),
                your_score_pill,        
                optimal_score_pill       
            ]
            table_data.append(row)

        col_widths = [(A4[0]-69) / 3] * 3
        section_.append(self._build_styled_table(table_data, col_widths))

        final_table = Table([[item] for item in section_], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("LEFTPADDING", (0, -1), (-1, -1), 34.5),
            ("RIGHTPADDING", (0, -1), (-1, -1), 34.5),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

    def get_homa_ir(self, homa_ir_data: dict):
        section = []

        title = homa_ir_data.get("title", "")
        sub_title = homa_ir_data.get("sub_title", "")
    
        homa_ir_score = homa_ir_data.get("homa_ir_score", "")
        home_ir_box_title=homa_ir_data.get("home_ir_box_title", "")
        gradient_colors=homa_ir_data.get("gradient_colors", "")  
        min_val=homa_ir_data.get("min_val", "")  
        max_val=homa_ir_data.get("max_val", "")  
        top_labels=homa_ir_data.get("top_labels", "")  
        bottom_labels=homa_ir_data.get("bottom_labels", "")
        pill_text=homa_ir_data.get("pill_text","")  

        # ---------- Heading ----------
        header = f'''
        <font name="{FONT_RALEWAY_MEDIUM}" size="30">{title}</font> 
        <font name="{FONT_INTER_SEMI_BOLD}" size="14">({sub_title})</font>
        '''
        heading = Paragraph(header, self.styles["homair"])
        section.append(heading)
        section.append(Spacer(1, 16))
        
        # ---------- Description Paragraph ----------
        header_data = homa_ir_data.get("title_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section.append(cs_data)
        section.append(Spacer(1, 32))
        
        
        value_inline = Paragraph(f"<b>{str(homa_ir_score)}</b>", self.styles["BrainScoreStyle"])
        drawing,color__ = GradientScoreBar(
                score=homa_ir_score,
                width=499,
                data_min=min_val,
                data_max=max_val,
                top_labels=top_labels,
                bottom_labels=bottom_labels,
                gradient_colors=gradient_colors
            ).draw()

        top_stack = Table([[value_inline,RoundedPill(pill_text, color__, 8, 80, 18)]], colWidths=[250,249])

        top_stack.setStyle(TableStyle([
            ("ALIGN",(1,0),(1,-1),"RIGHT"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            #("BOX",(0,0),(-1,-1),0.2,colors.black),
            ("LINEBELOW", (0, 0), (-1, -1), 0.01, colors.HexColor("#00625B"))
        ]))
        data = [
            [top_stack],
            [""],
            [Paragraph(f'<font color="#00625B">{home_ir_box_title}</font>', self.styles["ear_screening_title"])],           
            [drawing],          # Bottom content
        ]

        bottom_stack = Table(data, colWidths=[499])
        bottom_stack.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            # ("BOX",(0,0),(-1,-1),0.2,colors.black),
        ]))
        bottom_stack_ = Table([[bottom_stack]], colWidths=[A4[0]-64])
        bottom_stack_.setStyle(TableStyle([

            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            #("BOTTOMPADDING", (0, 0), (0, 2), 8),
            ("BOTTOMPADDING", (0, 0), (-1,-1), 16),
            #("BOX",(0,0),(-1,-1),0.2,colors.black)
        ]))


        rounded_card = RoundedBox(
                width=A4[0]-64,
                height=None,
                content=bottom_stack_,
                corner_radius=16
            )
        section.append(rounded_card)

        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

    def get_framingham_risk_score(self, framingham_risk_data: dict):
        section = []

        title = framingham_risk_data.get("title", "")    
        fr_risk_score = framingham_risk_data.get("fr_risk_score", "")
        fr_risk_box_title=framingham_risk_data.get("fr_risk_box_title", "")
        gradient_colors=framingham_risk_data.get("gradient_colors", "")  
        min_val=framingham_risk_data.get("min_val", "")  
        max_val=framingham_risk_data.get("max_val", "")  
        top_labels=framingham_risk_data.get("top_labels", "")  
        bottom_labels=framingham_risk_data.get("bottom_labels", "")
        pill_text=framingham_risk_data.get("pill_text","")  

        cs = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        header_data = framingham_risk_data.get("title_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section.append(cs_data)
        section.append(Spacer(1, 32))
        
        
        value_inline = Paragraph(
            f'<font>{fr_risk_score}%</font>'
            f'<font name="{self.styles["box_decimal_style"].fontName}" size="{self.styles["box_decimal_style"].fontSize}" color="{self.styles["box_decimal_style"].textColor}">percent</font>',
            self.styles["BrainScoreStyle"]
        )

        drawing,color__ = GradientScoreBar(
                score=fr_risk_score,
                width=499,
                data_min=min_val,
                data_max=max_val,
                top_labels=top_labels,
                bottom_labels=bottom_labels,
                gradient_colors=gradient_colors
            ).draw()

        top_stack = Table([[value_inline,RoundedPill(pill_text, color__, 8, 80, 18)]], colWidths=[250,249])

        top_stack.setStyle(TableStyle([
            ("ALIGN",(1,0),(1,-1),"RIGHT"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            #("BOX",(0,0),(-1,-1),0.2,colors.black),
            ("LINEBELOW", (0, 0), (-1, -1), 0.01, colors.HexColor("#00625B"))
        ]))
        data = [
            [top_stack],
            [""],
            [Paragraph(f'<font color="#00625B">{fr_risk_box_title}</font>', self.styles["ear_screening_title"])],           
            [drawing],          # Bottom content
        ]

        bottom_stack = Table(data, colWidths=[499])
        bottom_stack.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            # ("BOX",(0,0),(-1,-1),0.2,colors.black),
        ]))
        bottom_stack_ = Table([[bottom_stack]], colWidths=[A4[0]-64])
        bottom_stack_.setStyle(TableStyle([

            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            #("BOTTOMPADDING", (0, 0), (0, 2), 8),
            ("BOTTOMPADDING", (0, 0), (-1,-1), 16),
            #("BOX",(0,0),(-1,-1),0.2,colors.black)
        ]))


        rounded_card = RoundedBox(
                width=A4[0]-64,
                height=None,
                content=bottom_stack_,
                corner_radius=16
            )
        section.append(rounded_card)

        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

    def get_oligo_scan(self, oligo_scan_data: dict):
        section = []

        title = oligo_scan_data.get("title", "")    

        cs = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        header_data = oligo_scan_data.get("title_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section.append(cs_data)
        section.append(Spacer(1, 16))

        heavy_metal_report=oligo_scan_data.get("heavy_metal_report","")
        cs = Paragraph(heavy_metal_report.get("title",""), self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 8))

        img_path = os.path.join("staticfiles", "icons", "heavy_metal_report.png")        
        img = Image(img_path, width=561, height=342)

        section.append(img)
        bullet_items = []

        for finding in heavy_metal_report["findings"]:
            metals = finding["metals"]
            level = finding["level"]
            color_=finding["level_color"]
            sources_text = finding.get("sources", "")

            # Styled metal names
            metal_str = ", ".join(metals)
            metal_styled = f'<font name="Inter-Bold" color="#667085">{metal_str}</font>'

            # Styled level
            level_styled = f'<font name="Inter-Bold" color="{color_}">{level}</font>'

            if len(metals)==1:
                final_text = f'{metal_styled} is {level_styled}. {sources_text}'
            else:
                final_text = f'{metal_styled} are {level_styled}. {sources_text}'
            bullet_items.append(ListItem(Paragraph(final_text, self.styles["BulletStyle"])))

        # Add to document
        section.append(ListFlowable(bullet_items, bulletType='bullet', start='•'))
        # section.append(Spacer(1, 12))
        
        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("LEFTPADDING", (0, 6), (-1, 6), 17),
            ("RIGHTPADDING", (0, 6), (-1, 6), 17),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

    def get_domain_in_focus(self, domain_in_focus_data: dict):
        flowables = []

        title = domain_in_focus_data.get("title", "")
        cs = Paragraph(title, self.styles["TOCTitleStyle"])

        # --- Page 1 ---        
        # Title with 32pt indent
        flowables.append(Indenter(left=32, right=32))
        flowables.append(cs)
        flowables.append(Spacer(1, 8))
        flowables.append(Indenter(left=-32, right=-32))  # close title indent

        # Image with 17pt indent
        img_path1 = os.path.join("staticfiles", "icons", "domain_in_focus_1.png")
        img1 = Image(img_path1, width=559, height=594)
        flowables.append(Indenter(left=17, right=17))
        flowables.append(img1)
        flowables.append(Indenter(left=-17, right=-17))

        flowables.append(PageBreak())

        # --- Page 2 ---
        flowables.append(Spacer(1, 8))
        
        flowables.append(Indenter(left=32, right=32))
        flowables.append(cs)
        flowables.append(Spacer(1, 8))
        flowables.append(Indenter(left=-32, right=-32))

        img_path2 = os.path.join("staticfiles", "icons", "domain_in_focus_2.png")
        img2 = Image(img_path2, width=559, height=594)
        flowables.append(Indenter(left=17, right=17))
        flowables.append(img2)
        flowables.append(Indenter(left=-17, right=-17))

        return flowables

    def get_minerals_test_ratio(self, minerals_test_ratio_data: dict):
        section = []

        title = minerals_test_ratio_data.get("title", "")    

        cs = Paragraph(title, self.styles["TOCTitleStyle"])
        
        section.append(Indenter(left=32, right=32))
        section.append(cs)
        section.append(Spacer(1, 16))        
        section.append(Indenter(left=-32, right=-32))

        img_path = os.path.join("staticfiles", "icons", "mineral_test_ratio_report.png")        
        img = Image(img_path, width=558, height=531)
        section.append(Indenter(left=17, right=17))
        section.append(img)
        section.append(Indenter(left=-17, right=-17))
        
        
        section.append(Indenter(left=32, right=32))
        section.append(Spacer(1, 16))  
        bullet_items = []
        findings=minerals_test_ratio_data.get("findings","")
        for finding in findings:
            metals = finding["metals"]
            level = finding["level"]
            color_=finding["level_color"]
            sources_text = finding.get("sources", "")

            # Styled metal names
            metal_str = ", ".join(metals)
            metal_styled = f'<font name="Inter-Bold" color="#667085">{metal_str}</font>'

            # Styled level
            level_styled = f'<font name="Inter-Bold" color="{color_}">{level}</font>'

            if len(metals)==1:
                final_text = f'{metal_styled} is {level_styled}. {sources_text}'
            else:
                final_text = f'{metal_styled} are {level_styled}. {sources_text}'
            bullet_items.append(ListItem(Paragraph(final_text, self.styles["BulletStyle"])))

        # Add to document
        section.append(ListFlowable(bullet_items, bulletType='bullet', start='•'))
        section.append(Indenter(left=-32, right=-32))
        
        return section

    def get_aerobic_capacity(self, aerobic_data: dict):
        section = []

        title = aerobic_data.get("title", "")
        sub_title = aerobic_data.get("sub_title", "")
    
        aerobic_score = aerobic_data.get("aerobic_score", "")
        aerobic_box_title=aerobic_data.get("aerobic_box_title", "")
        aerobic_unit=aerobic_data.get("aerobic_unit", "")
        gradient_colors=aerobic_data.get("gradient_colors", "")  
        min_val=aerobic_data.get("min_val", "")  
        max_val=aerobic_data.get("max_val", "")  
        top_labels=aerobic_data.get("top_labels", "")  
        bottom_labels=aerobic_data.get("bottom_labels", "")
        pill_text=aerobic_data.get("pill_text","")  

        # ---------- Heading ----------
        header = f'''
        <font name="{FONT_RALEWAY_MEDIUM}" size="30">{title}</font> 
        <font name="{FONT_INTER_SEMI_BOLD}" size="14">({sub_title})</font>
        '''
        heading = Paragraph(header, self.styles["homair"])
        section.append(heading)
        section.append(Spacer(1, 16))
        
        # ---------- Description Paragraph ----------
        header_data = aerobic_data.get("title_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section.append(cs_data)
        section.append(Spacer(1, 32))
        
        
        value_inline = Paragraph(
            f'<font>{aerobic_score}</font>'
            f'<font name="{self.styles["box_decimal_style"].fontName}" size="{self.styles["box_decimal_style"].fontSize}" color="{self.styles["box_decimal_style"].textColor}">{aerobic_unit}</font>',
            self.styles["BrainScoreStyle"]
        )

        drawing,color__ = GradientScoreBar(
                score=aerobic_score,
                width=499,
                data_min=min_val,
                data_max=max_val,
                top_labels=top_labels,
                bottom_labels=bottom_labels,
                gradient_colors=gradient_colors
            ).draw()

        top_stack = Table([[value_inline,RoundedPill(pill_text, color__, 8, 80, 18)]], colWidths=[250,249])

        top_stack.setStyle(TableStyle([
            ("ALIGN",(1,0),(1,-1),"RIGHT"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            #("BOX",(0,0),(-1,-1),0.2,colors.black),
            ("LINEBELOW", (0, 0), (-1, -1), 0.01, colors.HexColor("#00625B"))
        ]))
        data = [
            [top_stack], 
            [""],
            [Paragraph(aerobic_box_title, self.styles["AerobicStyle"])], 
            [""],          
            [drawing],          # Bottom content
        ]

        bottom_stack = Table(data, colWidths=[499])
        bottom_stack.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            # ("BOX",(0,0),(-1,-1),0.2,colors.black),
        ]))
        bottom_stack_ = Table([[bottom_stack]], colWidths=[A4[0]-64])
        bottom_stack_.setStyle(TableStyle([

            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            #("BOTTOMPADDING", (0, 0), (0, 2), 8),
            ("BOTTOMPADDING", (0, 0), (-1,-1), 16),
            #("BOX",(0,0),(-1,-1),0.2,colors.black)
        ]))


        rounded_card = RoundedBox(
                width=A4[0]-64,
                height=None,
                content=bottom_stack_,
                corner_radius=16
            )
        section.append(rounded_card)

        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table

        
    def generate(self, data: dict) -> list:
        story = []
        story.extend(self.build_main_section(data))       
        toc_data=data.get("toc_items",[])
        if toc_data:
            story.append(PageBreak())
            story.extend(self.toc_table(toc_data))
        user_profile_card=data.get("user_profile_card",{})
        if user_profile_card:
            story.append(PageBreak())
            story.append(self.get_user_profile_card(user_profile_card))
        profile_card_data=data.get("profile_card_data",{})
        if profile_card_data:
            story.append(Spacer(1, 12))
            story.append(self.get_health_metrics_left_column(profile_card_data,data))
        current_symptoms_conditions=data.get("current_symptoms_conditions",{})
        if current_symptoms_conditions:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_current_symptoms_conditions(current_symptoms_conditions))
        your_current_stack=data.get("your_current_stack",{})
        if your_current_stack:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_your_current_stack(your_current_stack))

        family_and_past_histories=data.get("family_and_past_histories",{})
        if family_and_past_histories:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_family_past_histories(family_and_past_histories))

        health_goals=data.get("health_goals",{})
        if health_goals:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_health_goals(health_goals))
        
        vital_params=data.get("vital_params",{})
        if vital_params:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_vital_params(vital_params))
        
        ear_screening=data.get("ear_screening",{})
        if ear_screening:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_ear_screening(ear_screening))
            

        brain_function_score=data.get("brain_score",{})
        if brain_function_score:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_brain_function_screen(brain_function_score))

        bmi=data.get("bmi",{})
        if bmi:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_body_mass_index(bmi,data))

        # body_composition=data.get("body_composition",{})
        # if body_composition:
        #     story.append(PageBreak())
        #     story.append(Spacer(1, 8))
        #     story.extend(self.get_body_composition(data))
        
        fitness_assesment=data.get("fitness_assesment",{})
        if fitness_assesment:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_fitness_assesment(fitness_assesment))


        homa_ir=data.get("homa_ir",{})
        if homa_ir:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_homa_ir(homa_ir))
        
        framingham_risk_score=data.get("framingham_risk_score",{})
        if framingham_risk_score:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_framingham_risk_score(framingham_risk_score))

        oligo_scan=data.get("oligo_scan",{})
        if oligo_scan:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_oligo_scan(oligo_scan))

        domain_in_focus=data.get("domain_in_focus",{})
        if domain_in_focus:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_domain_in_focus(domain_in_focus))

        minerals_test_ratio=data.get("minerals_test_ratio",{})
        if minerals_test_ratio:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_minerals_test_ratio(minerals_test_ratio))
        
        aerobic_capacity=data.get("aerobic_capacity",{})
        if aerobic_capacity:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_aerobic_capacity(aerobic_capacity))
        
        
        # story.append(PageBreak())
        # story.extend(self.get_understanding_biomarker(data))
        # story.append(PageBreak())
        # story.extend(self.get_areas_of_concern(data))
        # story.append(PageBreak())
        # story.extend(self.get_morning_routine_protocol(data))
        
        return story


app = FastAPI()

@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    data = await request.json()  

    buffer = io.BytesIO()
    template = ThriveRoadmapTemplate()
    renderer = ThrivePageRenderer(template)

    doc = BaseDocTemplate(buffer, pagesize=A4,leftMargin=0, rightMargin=0,topMargin=0, bottomMargin=0)
    frame = Frame(
        x1=0,
        y1=FOOTER_HEIGHT,
        width=PAGE_WIDTH,
        height=PAGE_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT,
        id='main',
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=0,

    )

    doc.addPageTemplates([
        PageTemplate(id='main', frames=[frame], onPage=renderer.draw_header, onPageEnd=renderer.draw_footer)
    ])
    print("Left Margin:", doc.leftMargin)
    print("Right Margin:", doc.rightMargin)
    print("Top Margin:", doc.topMargin)
    print("Bottom Margin:", doc.bottomMargin)
    flowables = template.generate(data)  
    doc.build(flowables, canvasmaker=NumberedCanvas)
    with open("output_from_buffer_stash.pdf", "wb") as f:
        f.write(buffer.getvalue())
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "inline; filename=styled_output.pdf"
    })

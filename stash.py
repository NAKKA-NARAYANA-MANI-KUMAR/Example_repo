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
print(PAGE_WIDTH, PAGE_HEIGHT)
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
        if page_number == total_pages:
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

class RoundedPill1(Flowable):
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
        font_name=FONT_INTER_REGULAR,
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

        # Icon handling
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
        # Measure text width using pdfmetrics
        text_width = stringWidth(self.text, self.font_name, self.font_size)
        content_width = text_width + self.left_padding + self.right_padding

        if self.icon_drawing:
            content_width += self.icon_width + self.icon_text_padding

        # Estimate height
        content_height = max(self.font_size, self.icon_height) + self.top_padding + self.bottom_padding

        self.width = self.width if self.width is not None else content_width
        self.height = self.height if self.height is not None else content_height
        self.radius = self.radius if self.radius is not None else self.height / 2

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

        # Set font and compute string width
        self.canv.setFont(self.font_name, self.font_size)
        text_width = self.canv.stringWidth(self.text, self.font_name, self.font_size)

        content_width = text_width
        if self.icon_drawing:
            content_width += self.icon_width + self.icon_text_padding

        start_x = (self.width - content_width) / 2
        center_y = self.height / 2

        # Draw icon if exists
        if self.icon_drawing:
            icon_y = center_y - self.icon_height / 2
            renderPDF.draw(self.icon_drawing, self.canv, start_x, icon_y)
            start_x += self.icon_width + self.icon_text_padding

        # Draw text
        text_y = center_y - self.font_size / 4  # adjust vertically
        self.canv.setFillColor(self.text_color)
        self.canv.drawString(start_x, text_y, self.text)

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
    def __init__(self, icon, text_para, gap=6):
        super().__init__()
        self.icon = icon
        self.text_para = text_para
        self.gap = gap

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
        # Center the icon vertically
        icon_y = (self.height - self.icon_height) / 2
        text_y = (self.height - self.text_height) / 2

        # Draw icon and text
        self.icon.drawOn(self.canv, 0, icon_y)
        self.text_para.drawOn(self.canv, self.icon_width + self.gap, text_y)

class GradientScoreBarr:
    def __init__(
        self,
        width=478,
        height=6,
        pill_text="102",
        bottom_labels=None,
        target_label=None,
        top_labels=None,
        bottom_labels_2=None,
        gradient_colors=None,
        units=None,
        label_text="Very Low",
        label_margin=15
    ):
        self.width = width
        self.height = height
        self.pill_text = pill_text
        self.label_text = label_text
        self.top_labels = top_labels or []
        self.bottom_labels = bottom_labels or []
        self.bottom_labels_2 = bottom_labels_2 or []
        self.label_margin = label_margin
        self.units = units
        self.target_label = target_label

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

        # Units
        if self.units:
            y = total_height - padding
            count = len(self.units)
            for i, text in enumerate(self.units):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                d.add(String(x, y, text, fontName=label_font, fontSize=9, fillColor=black))

        # Top Labels
        if self.top_labels:
            y = total_height if self.units else total_height - padding
            count = len(self.top_labels)
            for i, text in enumerate(self.top_labels):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                text_width = len(text) * 4.5
                if i == 0:
                    pass
                elif i == count - 1:
                    x -= text_width
                else:
                    x -= text_width / 2
                d.add(String(x, y, text, fontName=label_font, fontSize=7, fillColor=font_color))

        # Bar
        bar_y = total_height - self.height - (padding if self.top_labels else 0) - pill_h // 2
        d.add(Rect(0, bar_y, self.width, self.height, rx=radius, ry=radius, fillColor=white, strokeColor=None))

        # Gradient rendering
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
                    pass
                elif i == count - 1:
                    x -= text_width
                else:
                    x -= text_width / 2
                d.add(String(x, y, text, fontName=label_font, fontSize=7, fillColor=font_color))

        # Second bottom row
        if self.bottom_labels_2:
            y = bar_y - (padding * 2 if self.bottom_labels else padding)
            count = len(self.bottom_labels_2)
            for i, text in enumerate(self.bottom_labels_2):
                x = i * (self.width / (count - 1)) if count > 1 else self.width / 2
                text_width = len(text) * 4.5
                if i == 0:
                    pass
                elif i == count - 1:
                    x -= text_width
                else:
                    x -= text_width / 2
                d.add(String(x, y, text, fontName=label_font, fontSize=7, fillColor=font_color))

        # ------------------- Pill Placement Logic (with centered text) -------------------
        if self.target_label and self.target_label in self.bottom_labels:
            index = self.bottom_labels.index(self.target_label)
            segment_count = len(self.bottom_labels)
            segment_width = self.width / segment_count
            score_x = (index + 0.5) * segment_width
            normalized_x = score_x / self.width
        else:
            # fallback to center if no match
            score_x = self.width / 2
            normalized_x = 0.5

        score_color = self.get_multicolor_gradient(normalized_x)
        score_fill = self.lighten_color(score_color)

        pill_w = 38
        pill_font_size = 10.435
        font_name = FONT_INTER_BOLD

        score_x = max(min(score_x, self.width - pill_w / 2), pill_w / 2)
        pill_y = bar_y + self.height / 2 - pill_h / 2

        # Pill shape
        d.add(Rect(score_x - pill_w / 2, pill_y, pill_w, pill_h,
                   rx=pill_h / 2, ry=pill_h / 2,
                   fillColor=score_fill, strokeColor=score_color, strokeWidth=1))

        # Accurate text width and vertical position
        text_width = stringWidth(self.pill_text, font_name, pill_font_size)
        score_text_x = score_x - (text_width / 2)
        score_text_y = pill_y + (pill_h - pill_font_size) / 2 + 1

        d.add(String(score_text_x, score_text_y, self.pill_text,
                     fontName=font_name,
                     fontSize=pill_font_size,
                     fillColor=colors.HexColor("#003632")))

        return d, score_color

class BackgroundImageCard(Flowable):
    def __init__(self, card, bg_image_path, width, height):
        super().__init__()
        self.card = card
        self.bg_image = ImageReader(bg_image_path)
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        # Draw the background image
        self.canv.drawImage(
            self.bg_image,
            0,
            0,
            width=self.width,
            height=self.height,
            preserveAspectRatio=True,
            mask='auto'
        )
        # Draw the card on top
        self.card.wrapOn(self.canv, self.width, self.height)
        self.card.drawOn(self.canv, 0, 0)

class ThriveRoadmapTemplate:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.base_path = Path("staticfiles/icons")
        self.init_styles()
        self.svg_dir = "staticfiles/icons/"

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
            name="ear_screening_unit",
            fontName=FONT_INTER_REGULAR,
            fontSize=8,
            leading=18,
            textColor=colors.HexColor("#667085"),
            spaceBefore=0,
            spaceAfter=0
        ))
        self.styles.add(ParagraphStyle(
            "TOCEntryText",
            fontName=FONT_INTER_REGULAR,
            fontSize=14,
            textColor=colors.HexColor("#002624"),
            leading=30,
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
            name="LSTStyles",
            fontName=FONT_INTER_REGULAR,
            fontSize=12,
            leading=18,
            textColor=colors.HexColor("#667085"),
            spaceBefore=0,
            spaceAfter=0
        ))
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
        self.styles.add(ParagraphStyle(
            "DigestiveHealthStyle",
            fontName=FONT_RALEWAY_MEDIUM,  # Ensure this matches your registered font
            fontSize=12,
            leading=18,
            textColor=PMX_GREEN,
            spaceBefore=0,
            spaceAfter=0,
        ))
        self.styles.add(ParagraphStyle(
            "BiomarkersStyle",
            fontName=FONT_RALEWAY_MEDIUM,               
            fontSize=16,
            leading=24,                       
            textColor=PMX_GREEN   
        ))
        self.styles.add(ParagraphStyle(
            "BiomarkerHeader",
            fontName=FONT_INTER_SEMI_BOLD,  
            fontSize= FONT_SIZE_MEDIUM,
            leading=24,  
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
            caseChange=1  
        )),
        self.styles.add(ParagraphStyle(
            "BiomarkerValue",
            fontName=FONT_INTER_SEMI_BOLD,          # Make sure this font is registered
            fontSize=FONT_SIZE_MEDIUM,
            leading=24,                         # Line height = 24px (200% of 12px)
            textColor=colors.HexColor("#003632"),
            alignment=TA_RIGHT
        )),
        self.styles.add(ParagraphStyle(
            "BiomarkerUnit",
            fontName=FONT_INTER_REGULAR,          # Ensure this is registered
            fontSize=10,
            leading=18,                         # 180% of 10px
            textColor=colors.HexColor("#667085")
        ))
        self.styles.add(ParagraphStyle(
            "BiomarkerHeaderData",
            fontName=FONT_INTER_REGULAR,
            fontSize=10,
            leading=14,  # line-height: 14px
            textColor=colors.HexColor("#667085"),
            alignment=TA_LEFT
        )),
        self.styles.add(ParagraphStyle(
            "AreasOfConcern",
            fontName=FONT_RALEWAY_SEMI_BOLD,  # Make sure this font is registered
            fontSize=12,
            leading=18,  # line height
            textColor=PMX_GREEN,
            spaceBefore=0,
            spaceAfter=0,
            alignment=TA_CENTER, 
        ))
        self.styles.add(ParagraphStyle(
            name="RoutineStyle",
            fontName=FONT_INTER_REGULAR,
            fontSize=12,                 # or FONT_SIZE_MEDIUM
            leading=18,
            textColor=colors.HexColor("#003632"),
            spaceAfter=0,
        ))

        self.styles.add(ParagraphStyle(
            name="RoutineBulletStyle",
            parent=self.styles["RoutineStyle"],
            leftIndent=16,           # total indent for all lines (bullet + text)
            firstLineIndent=-8,      # bullet "hangs" to the left
            bulletFontName=FONT_INTER_REGULAR,  # preserve your font
            bulletFontSize=12,
            fontSize=12
        ))

        self.styles.add(ParagraphStyle(
            name="RoutineSubBulletStyle",
            parent=self.styles["RoutineStyle"],
            leftIndent=24,           # deeper indent
            firstLineIndent=-8,
            bulletFontName=FONT_INTER_REGULAR,  # preserve your font
            bulletFontSize=11,
            fontSize=11
        ))
        self.styles.add(ParagraphStyle(
            name="RoutineTitleStyle",
            fontName=FONT_INTER_SEMI_BOLD,            # Inter Semibold
            fontSize= FONT_SIZE_LARGE_MEDIUM,                          # 16px
            leading=24,                           # Line height: 150%
            textColor=PMX_GREEN, # Brand-50                       # Optional spacing after paragraph
        ))
        self.styles.add(ParagraphStyle(
            "DiagnosisText",
            fontName=FONT_INTER_REGULAR,                      # Make sure the Inter font is registered
            fontSize=10.952,
            leading=26.941,
            textColor=colors.HexColor("#26968D"),
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            "BodyWeightVal",
            fontName=FONT_INTER_SEMI_BOLD,               # Make sure the 'Inter-SemiBold' font is registered
            fontSize=18,
            leading=28,                              # Line height
            textColor=colors.HexColor("#003632"),    # Brand-800 color
            alignment=TA_LEFT,                       # Default alignment from your CSS (not explicitly center or right)
        ))
        self.styles.add(ParagraphStyle(
            "AdditionalDiagnostics",
            fontName=FONT_RALEWAY_SEMI_BOLD,  # Make sure this font is registered
            fontSize=12,
            leading=18,  # line height
            textColor=colors.HexColor("#002624"),
            spaceAfter=0,
            spaceBefore=0,
        ))
        self.styles.add(ParagraphStyle(
            "CardioVascularStyle",
            fontName=FONT_INTER_BOLD,  # Assuming you've registered "Inter-Bold"
            fontSize=12,
            leading=18,
            leftIndent=12,
            textColor=colors.HexColor("#003632"),
        ))
        self.styles.add(ParagraphStyle(
            "SSBUlletBelowStyle",
            fontName=FONT_INTER_REGULAR,  # Ensure Inter is registered; fallback to 'Helvetica' if not
            fontSize=7.375,
            leading=10.536,
            textColor=HexColor("#004540"),
            alignment=TA_CENTER,
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
            "ActionPlanStyle",
            fontName=FONT_INTER_SEMI_BOLD,       # You must register this font first
            fontSize=16,
            leading=24,                      # This is the line-height (150% of font size)
            textColor=PMX_GREEN,
            spaceAfter=0                     # Optional: spacing after paragraph
        ))
        self.styles.add(ParagraphStyle(
            "SADataStyle",
            fontName=FONT_INTER_REGULAR,           
            fontSize=8,
            leading=10,                 
            textColor=white,            
            alignment=TA_CENTER,        
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
            ("LINEBELOW", (0, 0), (-1, 0), 0.01, PMX_GREEN),
            ("LINEAFTER", (0, 0), (0, -1), 0.01, PMX_GREEN),
            ("LINEAFTER", (1,0), (1, -1), 0.01, PMX_GREEN),
            # Rounded Corners
            ("ROUNDEDCORNERS", [20, 20, 20, 20]),
            ("FONTNAME", (0, -1), (-1, -1), FONT_INTER_BOLD),
            ("BOX", (0, 0), (-1, -1), 0.01, PMX_GREEN, None, None, "round"),
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
            ahw_path = os.path.join("staticfiles", "icons", "male_age_ht_wt_.png")
        elif gender.lower()=="female":
            ahw_path = os.path.join("staticfiles", "icons", "female_age_ht_wt_.png")
        else:
            ahw_path = os.path.join("staticfiles", "icons", "other_age_ht_wt.png")
        # image_= Image(ahw_path, width=222, height=308)
        
        text_data = [
            (profile_card_data.get("age","00 yr"), 180, 285, "ear_screening_title"),       # Height
            (profile_card_data.get("height","00 cm"), 180, 150, "ear_screening_title"),        # Waist
            (profile_card_data.get("weight","00 kg"), 170, 22, "ear_screening_title")       # Hip
        ]

        icon_ahw = ImageWithOverlayText(
            image_path=ahw_path,
            width=222,
            height=308,
            text_data=text_data,
            styles=self.styles["ear_screening_title"]
        )

        right_metric_table=Table([[icon_ahw]])
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

    def get_lifestyle_trends(self, lifestyle_data: dict):

        section = []
        header=lifestyle_data.get("header","")
        cs=Paragraph(header, self.styles["TOCTitleStyle"])
        section.append([cs])
        section.append([Spacer(1,8)])

        header_data=lifestyle_data.get("header_data","")
        cs_data=Paragraph(header_data, self.styles["header_data_style"])
        section.append([cs_data])
        section.append([Spacer(1,40)])
        
        icon_path = os.path.join(svg_dir,"bullet.svg")  
        icon_bullet = self.svg_icon(icon_path, width=16, height=16)

        icon_path = os.path.join("staticfiles/icons/", "lifestyle.svg")
        icon_lifestyle = self.svg_icon(icon_path, width=24, height=24)
        
        lifestyle_trends_data_=lifestyle_data.get("lifestyle_trends_data","")

        total_height = 473  # Fixed total height
        available_width = 346  # 160 + 32 + 160 (two columns + spacer)

        row_tables = []
        temp_row = []

        # Step 1: Prepare item tables
        for item in lifestyle_trends_data_:
            name = item.get("name", "")
            data = item.get("data", [])
            data_str = ", ".join(str(d) for d in data)

            name_para = Paragraph(name, self.styles["bullet_after_text"])
            data_para = Paragraph(data_str, self.styles["LSTStyles"])

            item_table = Table([
                [icon_bullet, Spacer(1, 8), name_para],
                ["", Spacer(1, 8), data_para]
            ], colWidths=[16, 8, None])

            item_table.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            temp_row.append(item_table)
            if len(temp_row) == 2:
                row_tables.append(temp_row)
                temp_row = []

        # Handle last odd item
        if temp_row:
            if len(temp_row) == 1:
                temp_row.append(Spacer(1, 1))
            row_tables.append(temp_row)

        # Build rows with column spacers
        lifestyle_rows = []
        for row in row_tables:
            lifestyle_rows.append([row[0], Spacer(1, 26), row[1]])

        # Create the table to overlay inside fixed height
        final_table_ = Table(lifestyle_rows, colWidths=[160, 26, 160])
        final_table_.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1,-1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
 

        def make_status_card(title, desc, icon_file, status_text, color,width,height):
            icon = self.svg_icon(os.path.join("staticfiles/icons/", icon_file), width=width, height=height)
            title_para = Paragraph(f'<font color="#FFFFFF">{title}</font>', self.styles["AreasOfConcern"])
            desc_para = Paragraph(desc, self.styles["SADataStyle"])
            status_para = RoundedPill(status_text, color, 8, 70, 18, 8)


            card = Table([
                [icon],
                [title_para],
                [desc_para],
                [Spacer(1,6)],
                [status_para]
            ], colWidths=[75])

            card.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (0, -1), 0),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 0),
            ]))

            padded = Table([[card]], colWidths=[89])
            padded.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0,0 ), (0,-1), 16),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
            ]))
            return padded

        smoking_card = make_status_card(
            "Smoking Status",
            "A brief overview of your smoking habits to assess potential risks and guide health recommendations.",
            "smoking_final.svg", "Non Smoker", colors.HexColor("#17B26A"),width=24,height=24
        )

        alcohol_card = make_status_card(
            "Alcohol Status",
            "Overview of your alcohol consumption to assess risks and guide recommendations.",
            "alcohol_final.svg", "Weekly", colors.HexColor("#F79009"),width=9.13,height=18
        )

        # Wrap it with a background image
        img_path_ = os.path.join(svg_dir,"smoking_status.png") 
        smoking_card_with_bg = BackgroundImageCard(smoking_card, img_path_, width=89, height=212)

        img_path = os.path.join(svg_dir,"alcohol_status.png") 
        alcohol_card_with_bg = BackgroundImageCard(alcohol_card, img_path, width=89, height=212)

        right_cards_table = Table([
            [smoking_card_with_bg],
            [alcohol_card_with_bg]
        ], colWidths=[121])
        right_cards_table.setStyle(TableStyle([
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("TOPPADDING", (0,0 ), (0,-1), 16),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            # ("BOX",(0,0),(-1,-1),0.2,black)
        ]))

        right_box = RoundedBox(
            width=121,
            height=None,
            content=right_cards_table,
            corner_radius=10,
            border_radius=0.1,
            fill_color=colors.white,
            stroke_color=PMX_GREEN
        )
        # ---------- Extract Data ----------
        icon_path = os.path.join(svg_dir, "lifestyle.svg")
        icon = self.svg_icon(icon_path, width=24, height=24)
        frst_row = Table(
            [   
                [icon,Spacer(1,10),Paragraph("Your Lifestyle Trends", self.styles["SvgBulletTitle"])]
            ],
            colWidths=[24,10, None],
        )
        frst_row.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        full_row = Table(
            [   
                [frst_row,"",""],
                [Spacer(1,8)],
                [final_table_,Spacer(1,32), right_box]],
            colWidths=[346,32, 121],
        )
        full_row.setStyle(TableStyle([
            ("SPAN", (0, 0), (-1, 0)),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        full_row_ = Table(
            [[full_row]],
            colWidths=[A4[0]-64],
        )
        full_row_.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))


        outer = RoundedBox(
            width=A4[0]-64,
            height=None,
            content=full_row_,
            corner_radius=10,
            fill_color=colors.white,
            stroke_color=colors.HexColor("#D9E9E6")
        )

        section.append(outer)
        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table
        # return section

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
                ("LINEBELOW", (0, 3), (-1, 3), 0.01, PMX_GREEN),
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
                "path":"eye.svg",
                "width":18,
                "height":9.15
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
            ("LINEBELOW", (0, 0), (-1, 0), 0.1, PMX_GREEN),
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
            ("LINEBELOW", (0, 0), (-1, 0), 0.3, PMX_GREEN)
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
            #         ("LINEBELOW", (0, 0), (-1, 0), 0.01, PMX_GREEN)
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
        else:
            icon_path = os.path.join(svg_dir,'other_bmi.png')
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

    def get_body_composition(self, body_composition: dict):

        title = body_composition.get("title", "")
        section=[]
        section.append(Indenter(left=32, right=32))
        # ---------- Heading ----------
        heading = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(heading)
        section.append(Spacer(1, 8))

        # ---------- Icon and Title Data ----------
        icon_path = os.path.join(svg_dir, "BMI.svg")
        icon = self.svg_icon(icon_path, width=24, height=24)

        title_data = body_composition.get("title_data", "")
        title_data_text = Paragraph(title_data, self.styles["eye_screening_desc_style"])

        icon_path_bmi = os.path.join(svg_dir, "diagnosis_image.png")
        # icon_bmi = self.svg_icon(icon_path_bmi, width=251, height=294)
        

        bg = PILImage.open(icon_path_bmi).convert("RGBA")
        overlay = PILImage.new("RGBA", bg.size, "#02665F")  # simulate a solid overlay color

        # Blend them (simulate soft-light-like effect)
        blended = PILImage.blend(bg, overlay, alpha=0)  # adjust alpha for intensity

        # Save to BytesIO stream
        img_buffer = BytesIO()
        blended.save(img_buffer, format='PNG')
        img_buffer.seek(0)

        # Create ReportLab image from stream
        rl_img = RLImage(img_buffer, width=251, height=294)  # set width/height as needed


        image_data=body_composition.get("image_data","")

        image_data_val = Paragraph(
            image_data,
            self.styles["DiagnosisText"]  # Or self.styles["decimal_style_"] if defined
        )
        body_weight_=body_composition.get("body_weight","")
        body_weight = Paragraph(
            f'<para align="right">'
            f'<font name="{self.styles["BodyWeightVal"].fontName}" size="{self.styles["BodyWeightVal"].fontSize}" color="{self.styles["BodyWeightVal"].textColor}"><b>{body_weight_.get("Val","00")}</b></font> '
            f'<font name="{self.styles["ear_screening_unit"].fontName}" size="{self.styles["ear_screening_unit"].fontSize}" color="{self.styles["ear_screening_unit"].textColor}">{body_weight_.get("unit","kg")}</font>'
            f'</para>',
            self.styles["ear_screening_unit"]
        )

        body_weight_title = Paragraph(
            body_weight_.get("key","Body Weight"),
            self.styles["box_title_style"]
        )

        body_weight_row = Table([
                [body_weight_title, body_weight]
            ],
            colWidths=[106, 127],  # Adjust widths as needed
        )
        body_weight_row.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ]))
        body_weight_row_ = Table([
                [body_weight_row]
            ],
            colWidths=[265.5],  # Adjust widths as needed
        )
        body_weight_row_.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            # ("BOX",(0,0),(0,-1),0.1,colors.black),
            # ("BOX",(-1,0),(-1,-1),0.1,colors.black)
        ])
        )
        body_weight_row1=RoundedBox(width=265.5, height=None, content=body_weight_row_, corner_radius=16)
        svg_heading_row = Table(
            [
                [icon, "", title_data_text],
                [rl_img,"",""],
                [image_data_val, "", ""],
                [""],
                [body_weight_row1,"",""],
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
                colWidths=[194]
            )
            inner_table.setStyle(TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
        
            padded_inner = Table([[inner_table]], colWidths=[226])
            padded_inner.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1),12),
            ]))

            rounded_card = RoundedBox(
                width=226,
                height=None,
                content=padded_inner,
                corner_radius=16,
                border_radius=0.4
            )

            story.append(rounded_card)
            if idx < len(metrics) - 1:
                story.append(Spacer(1, 4))

        # Final layout with left icon and right cards
        body_comp_row = Table([[svg_heading_row,Spacer(1,38),story]], colWidths=[266,38,226], rowHeights=[None])
        body_comp_row.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0)
        ]))
        section.append(body_comp_row)
        tscore_val=body_composition.get("tscore_val","")

        gradient_colors = body_composition.get("gradient_colors","")
        min_val = body_composition.get("min_val","")
        max_val = body_composition.get("max_val","")
        units = body_composition.get("units","")
        top_labels = body_composition.get("top_labels","")
        bottom_labels = body_composition.get("bottom_labels","")
        bottom_labels_2= body_composition.get("bottom_labels_2","")

        drawing,color__ = GradientScoreBar(
                score=tscore_val,
                width=513,
                data_min=min_val,
                data_max=max_val,
                units=units,
                top_labels=top_labels,
                bottom_labels=bottom_labels,
                bottom_labels_2=bottom_labels_2,
                gradient_colors=gradient_colors
            ).draw()


        tscore_title=body_composition.get("tscore","")
        tscore_data=body_composition.get("tscore_data","")
        
        title_=Paragraph(tscore_title, self.styles["SvgBulletTitle"])
        title_data=Paragraph(tscore_data, self.styles["eye_screening_desc_style"])
        
        rows = [
            [title_],
            [title_data],
            [drawing]
        ]
        content_ = Table(rows, colWidths=[529])
        
    
        content_.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            
        ]))

    
        section.append(content_)
        section.append(Indenter(left=-32, right=-32))
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

            your_score_pill = RoundedPill(your_score, PMX_BUTTON_BG, 8, 40, 18, 8, "#003632","#17B26A",0.2,FONT_INTER_BOLD)
            optimal_score_pill = RoundedPill(optimal_score, PMX_BUTTON_BG, 8, 40, 18, 8, "#003632","#17B26A",0.2,FONT_INTER_BOLD)

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
            ("LINEBELOW", (0, 0), (-1, -1), 0.01, PMX_GREEN)
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
            ("LINEBELOW", (0, 0), (-1, -1), 0.01, PMX_GREEN)
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
            ("LINEBELOW", (0, 0), (-1, -1), 0.01, PMX_GREEN)
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

    def get_resting_health(self, resting_health_data: dict):
        section_ = []
        
        # Header Section
        header = resting_health_data.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section_.append(cs)
        section_.append(Spacer(1, 16))

        header_data = resting_health_data.get("header_data", "")
        cs_data = Paragraph(header_data, self.styles["header_data_style"])
        section_.append(cs_data)
        section_.append(Spacer(1, 32))

        # Icon and Data
        icon_path = os.path.join(svg_dir, "calorie.svg")
        icon = self.svg_icon(icon_path, width=24, height=24)

        resting_health_data_ = resting_health_data.get("resting_health_data", [])
        draw_list = []

        title = Paragraph(resting_health_data.get("title", ""),self.styles["ear_screening_title"])
        title_data = Paragraph(resting_health_data.get("title_data", ""),self.styles["eye_screening_desc_style"])
        draw_list.append([title])
        draw_list.append([title_data])

        resting_health_val = resting_health_data.get("resting_health_val", "")
        resting_health_unit = resting_health_data.get("resting_health_unit", "")
        

        # Combine both with inline styling
        resting_health_para = Paragraph(
            f'<font name="{self.styles["BrainScoreStyle"].fontName}" size="{self.styles["BrainScoreStyle"].fontSize}" color="{self.styles["BrainScoreStyle"].textColor}">{resting_health_val}</font>'
            f'<font name="{self.styles["ear_screening_unit"].fontName}" size="{self.styles["ear_screening_unit"].fontSize}" color="{self.styles["ear_screening_unit"].textColor}"> {resting_health_unit}</font>',
            self.styles["BrainScoreStyle"]
        )
        draw_list.append([resting_health_para])
        draw_list.append([Spacer(1, 16)])

        # # Body Cards with Gradient Bar
        for idx, item in enumerate(resting_health_data_):
            title = item.get("title", "")
            title_data = item.get("title_data", "")
            score = item.get("score", 0)
            gradient_colors=item.get("gradient_colors", [])
            min_score=item.get("min_val", 0)
            max_score=item.get("max_val", 0)
            pill_text=item.get("pill_text","")
            bottom_labels = item.get("bottom_labels", "")

            title_ = Paragraph(title, self.styles["ear_screening_title"])
            title_data_para = Paragraph(title_data, self.styles["eye_screening_desc_style"])

            drawing, color__ = GradientScoreBar(width=467,score=float(score), data_min=min_score, data_max=max_score,
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
                [title_data_para]
            ], colWidths=[387])
            desc_block.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))
            if pill_text:
                card = Table([
                    [desc_block, RoundedPill(pill_text, hex_color, 8, 80, 18, 8, colors.HexColor('#EFEFEF'))]
                ], colWidths=[387, 80])
            else:
                card = Table([
                    [desc_block]
                ], colWidths=[467])
            card.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            content = Table([
                [card],
                [drawing]
            ], colWidths=[467])
            content.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            wrapper = Table([[content]], colWidths=[467])
            
            # wrapper.setStyle(TableStyle([
            #     ("LINEABOVE", (0, 0), (-1, 0), 0.01, PMX_GREEN),
            #     ("LEFTPADDING", (0, 0), (-1, -1), 0),
            #     ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            #     ("TOPPADDING", (0, 0), (-1, -1), 8),
            #     ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            # ]))
            # if idx==1:
            table_styles = [
                ("LINEABOVE", (0, 0), (-1, 0), 0.01, PMX_GREEN),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]

            if idx == 0:
                table_styles.extend([
                    ("TOPPADDING", (0, 0), (-1, -1), 16),
                ])
            else:
                table_styles.extend([
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ])
            wrapper.setStyle(TableStyle(table_styles))



            draw_list.append(wrapper)

        draw_list_=Table([[icon,Spacer(1,8),draw_list]], colWidths=[24,8,None])
        draw_list_.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, 0), 0),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 0),
            # ("BOX",(0,0),(-1,-1),0.3,colors.black)

        ]))
        # Outer Wrapper Box
        drawlist_table = Table([[draw_list_]], colWidths=[A4[0] - 64])
        drawlist_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, 0), 16),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
            # ("BOX",(0,0),(-1,-1),0.3,colors.black)
        ]))

        rounded_container = RoundedBox(width=A4[0] - 64, height=None, content=drawlist_table, corner_radius=12)
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
    
    def get_fatty_acid(self, fatty_acid_data: dict):
        section = []
        
        # Header Section
        header = fatty_acid_data.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        header_data = fatty_acid_data.get("header_data", "")
        content = []
        for item in header_data:
            header = item.get("header", "")
            value = item.get("value")
            content.append(f"<font name='Inter-Bold'>{header}:</font> {value}<br/>")
        full_paragraph = ''.join(content)
        section.append(Paragraph(full_paragraph, self.styles["eye_screening_desc_style"]))
        section.append(Spacer(1, 24))
        # Icon and Data
        icon_path = os.path.join(svg_dir, "calorie.svg")
        icon = self.svg_icon(icon_path, width=24, height=24)

        fatty_acid_data_ = fatty_acid_data.get("fatty_acid_data", [])
        draw_list = []

        # # Body Cards with Gradient Bar
        for idx, item in enumerate(fatty_acid_data_):
            title = item.get("title", "")
            title_data = item.get("title_data", "")
            score = item.get("score", 0)
            gradient_colors=item.get("gradient_colors", [])
            min_score=item.get("min_val", 0)
            max_score=item.get("max_val", 0)
            pill_text=item.get("pill_text","")
            bottom_labels = item.get("bottom_labels", "")
            top_labels = item.get("top_labels", "")

            title_ = Paragraph(title, self.styles["ear_screening_title"])
            title_data_para = Paragraph(title_data, self.styles["eye_screening_desc_style"])

            drawing, color__ = GradientScoreBar(width=483,score=float(score), data_min=min_score, data_max=max_score,
                                                bottom_labels=bottom_labels,
                                                top_labels=top_labels,
                                                gradient_colors=gradient_colors).draw()

            def color_to_hex(color):
                r = int(color.red * 255)
                g = int(color.green * 255)
                b = int(color.blue * 255)
                return '#{:02X}{:02X}{:02X}'.format(r, g, b)

            hex_color = color_to_hex(color__)

            desc_block = Table([
                [title_],
                [title_data_para]
            ], colWidths=[403])
            desc_block.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))
            if pill_text:
                card = Table([
                    [desc_block, RoundedPill(pill_text, hex_color, 8, 80, 18, 8, colors.HexColor('#EFEFEF'))]
                ], colWidths=[403, 80])
            else:
                card = Table([
                    [desc_block]
                ], colWidths=[483])
            card.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            content = Table([
                [card],
                [drawing]
            ], colWidths=[483])
            content.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            wrapper = Table([[content]], colWidths=[483])
            
            table_styles = [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]
            wrapper.setStyle(TableStyle(table_styles))



            draw_list.append(wrapper)

        
        drawlist_table = Table([[draw_list]], colWidths=[A4[0] - 80])
        drawlist_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, 0), 16),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
            # ("BOX",(0,0),(-1,-1),0.3,colors.black)
        ]))

        rounded_container = RoundedBox(width=A4[0] - 80, height=None, content=drawlist_table, corner_radius=12)
        section.append(rounded_container)

        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table
    
    def get_digestive_health(self, digestive_health_data: dict):
        section = []
        
        # Header Section
        header = digestive_health_data.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        header_data = digestive_health_data.get("header_data", "")
        content = []
        for item in header_data:
            header = item.get("header", "")
            value = item.get("value")
            content.append(f"<font name='Inter-Bold'>{header}:</font> {value}<br/>")
        full_paragraph = ''.join(content)
        section.append(Paragraph(full_paragraph, self.styles["eye_screening_desc_style"]))
        section.append(Spacer(1, 24))

        digestive_health_data_ = digestive_health_data.get("digestive_health_data", [])
        draw_list = []

        # # Body Cards with Gradient Bar
        for idx, item in enumerate(digestive_health_data_):
            title = item.get("title", "")
            title_data = item.get("title_data", "")
            score = item.get("score", 0)
            gradient_colors=item.get("gradient_colors", [])
            min_score=item.get("min_val", 0)
            max_score=item.get("max_val", 0)
            pill_text=item.get("pill_text","")
            bottom_labels = item.get("bottom_labels", "")

            title_ = Paragraph(title, self.styles["ear_screening_title"])
            title_data_para = Paragraph(title_data, self.styles["eye_screening_desc_style"])

            drawing, color__ = GradientScoreBar(width=467,score=float(score), data_min=min_score, data_max=max_score,
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
                [title_data_para]
            ], colWidths=[403])
            desc_block.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            desc_block_2 = Table([
                [Paragraph(f'<para alignment="right">{str(score)}</para>', self.styles["BrainScoreStyle"])],
                [RoundedPill(pill_text, hex_color, 8, 80, 18, 8, colors.HexColor('#EFEFEF'))]
            ], colWidths=[80])
            desc_block_2.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1,-1), "MIDDLE"),
                ("ALIGN",(0,0),(-1,-1),"RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))
            if pill_text:
                card = Table([
                    [desc_block, desc_block_2]
                ], colWidths=[403, 80])
            else:
                card = Table([
                    [desc_block]
                ], colWidths=[483])
            card.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            content = Table([
                [card],
                [Spacer(1,8)],
                [drawing]
            ], colWidths=[483])
            content.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            wrapper = Table([[content]], colWidths=[483])
            
            table_styles = [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]
            wrapper.setStyle(TableStyle(table_styles))



            draw_list.append(wrapper)
            draw_list.append(Spacer(1,8))
        
        microbiome_data = digestive_health_data.get("microbiome_data", [])
        microbiome_title= microbiome_data.get("title", [])
        microbiome_title_data= microbiome_data.get("title_data", [])

        title_ = Paragraph(microbiome_title, self.styles["ear_screening_title"])
        title_data_para = Paragraph(microbiome_title_data, self.styles["eye_screening_desc_style"])
        draw_list.append(Spacer(1,8))
        draw_list.append(title_)
        draw_list.append(title_data_para)
        draw_list.append(Spacer(1,8))
        microbiome_data_ = microbiome_data.get("microbiome_data_", [])
        microbiome_data_title = microbiome_data.get("microbiome_data_title", "")
        if microbiome_data_title:
            title_data_para_ = Paragraph(microbiome_data_title, self.styles["ear_screening_title"])
            draw_list.append(Spacer(1,8))
            draw_list.append(title_data_para_)
            draw_list.append(Spacer(1,8))
        key_list=[]
        val_list=[]
        for item in microbiome_data_:
            key=Paragraph(item.get("key",""),self.styles["DigestiveHealthStyle"])
            val=item.get("val","")
            unit=item.get("val_unit","")
            microbiome_data_para = Paragraph(
                f'<font name="{self.styles["BrainScoreStyle"].fontName}" size="{self.styles["BrainScoreStyle"].fontSize}" color="{self.styles["BrainScoreStyle"].textColor}">{val}</font>'
                f'<font name="{self.styles["ear_screening_unit"].fontName}" size="{self.styles["ear_screening_unit"].fontSize}" color="{self.styles["ear_screening_unit"].textColor}"> {unit}</font>',
                self.styles["BrainScoreStyle"]
            )
            key_list.append(key)
            val_list.append(microbiome_data_para)

        rows = []

        for key, val in zip(key_list, val_list):
            row = [key, Spacer(1, 8), val]
            rows.append(row)
            rows.append([Spacer(1, 10)])  # Row spacing after each row

        # Remove the last spacer after the final row
        if rows and isinstance(rows[-1][0], Spacer):
            rows.pop()

        # Create the table
        microbiome_table = Table(rows, colWidths=[226, 8, None])

        # Optional: Style the table (vertical alignment, padding)
        microbiome_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        draw_list.append(microbiome_table)
        drawlist_table = Table([[draw_list]], colWidths=[A4[0] - 80])
        drawlist_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, 0), 16),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
            # ("BOX",(0,0),(-1,-1),0.3,colors.black)
        ]))

        rounded_container = RoundedBox(width=A4[0] - 80, height=None, content=drawlist_table, corner_radius=12)
        section.append(rounded_container)

        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table
    
    def get_digestion_potential(self, digestion_potential_data: dict):
        section = []
        
        # Header Section
        header = digestion_potential_data.get("header", "")
        cs = Paragraph(header, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        header_data = digestion_potential_data.get("header_data", "")
        content = []
        for item in header_data:
            header = item.get("header", "")
            value = item.get("value")
            content.append(f"<font name='Inter-Bold'>{header}:</font> {value}<br/>")
        full_paragraph = ''.join(content)
        section.append(Paragraph(full_paragraph, self.styles["eye_screening_desc_style"]))
        section.append(Spacer(1, 24))

        digestion_potential_data_ = digestion_potential_data.get("digestion_potential_data", [])
        draw_list = []

        # # Body Cards with Gradient Bar
        for idx, item in enumerate(digestion_potential_data_):
            title = item.get("title", "")
            title_data = item.get("title_data", "")
            score = item.get("score", 0)
            gradient_colors=item.get("gradient_colors", [])
            pill_text=item.get("pill_text","")
            bottom_labels = item.get("bottom_labels", "")
            top_labels = item.get("top_labels", "")

            title_ = Paragraph(title, self.styles["ear_screening_title"])
            title_data_para = Paragraph(title_data, self.styles["eye_screening_desc_style"])

            drawing,color__ = GradientScoreBarr(width=467,
                                                height=6,
                                                target_label=pill_text,
                                                pill_text=score,                    
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
                [title_data_para]
            ], colWidths=[403])
            desc_block.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))
            if pill_text:
                card = Table([
                    [desc_block, RoundedPill(pill_text,hex_color , 8, 80, 18, 8, colors.HexColor('#EFEFEF'))]
                ], colWidths=[403, 80])
            else:
                card = Table([
                    [desc_block]
                ], colWidths=[483])
            card.setStyle(TableStyle([
                ("VALIGN", (1, 0), (1, 0), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            content = Table([
                [card],
                [drawing]
            ], colWidths=[483])
            content.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]))

            wrapper = Table([[content]], colWidths=[483])
            
            table_styles = [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                # ("BOX",(0,0),(-1,-1),0.3,colors.black)
            ]
            wrapper.setStyle(TableStyle(table_styles))



            draw_list.append(wrapper)

        
        drawlist_table = Table([[draw_list]], colWidths=[A4[0] - 80])
        drawlist_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, 0), 16),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
            # ("BOX",(0,0),(-1,-1),0.3,colors.black)
        ]))

        rounded_container = RoundedBox(width=A4[0] - 80, height=None, content=drawlist_table, corner_radius=12)
        section.append(rounded_container)

        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))

        return final_table
    
    def get_understanding_biomarker(self, biomarkers_range: dict):
        section = []

        title = biomarkers_range.get("title", "")
        biomarkers_range_data = biomarkers_range.get("biomarkers_range_data", [])
        biomarkers_data = biomarkers_range.get("biomarkers_data", [])
        heading = Paragraph(title, self.styles["TOCTitleStyle"])

        section.append(heading)
        section.append(Spacer(1, 16))
        icon_path = os.path.join(svg_dir, "bullet_point.svg")  
        icon = self.svg_icon(icon_path, width=16, height=16)

        # Extract headers and values
        header1 = biomarkers_range_data[0].get("header", "")
        val1    = biomarkers_range_data[0].get("value", "")

        header2 = biomarkers_range_data[1].get("header", "")
        val21   = biomarkers_range_data[1].get("value1", "")
        val22   = biomarkers_range_data[1].get("value2", "")

        header3 = biomarkers_range_data[2].get("header", "")
        val3    = biomarkers_range_data[2].get("value", "")

        # Table data (fixed commas and row structure)
        table_data = [
            [icon, Spacer(1, 10), Paragraph(header1, self.styles["BiomarkersStyle"])],
            ["", "", ""],
            [Paragraph(val1, self.styles["LSTStyles"]), '', ''],

            ["", "", ""],
            [icon, Spacer(1, 10), Paragraph(header2, self.styles["BiomarkersStyle"])],
            ["", "", ""],
            [Paragraph(f"• {val21}", self.styles["LSTStyles"]), '', ''],
            [Paragraph(f"• {val22}", self.styles["LSTStyles"]), '', ''],

            ["", "", ""],
            [icon, Spacer(1, 10), Paragraph(header3, self.styles["BiomarkersStyle"])],
            ["", "", ""],
            [Paragraph(val3, self.styles["LSTStyles"]), '', '']
        ]

        row_heights = [None, 8, None, 8, None, 8, None, None, 8, None, 8, None]

        header_data = Table(table_data, colWidths=[16, 10, 505], rowHeights=row_heights)
        header_data.setStyle(TableStyle([
            # Span value rows
            ("SPAN", (0, 2), (2, 2)),
            ("SPAN", (0, 6), (2, 6)),
            ("SPAN", (0, 7), (2, 7)),
            ("SPAN", (0, 11), (2, 11)),

            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        pill_color     = biomarkers_data.get("pill_color", "#FFFFFF")
        box_title     = Paragraph(biomarkers_data.get("title", ""),self.styles["BiomarkerHeader"])
        box_subtitle  = Paragraph(biomarkers_data.get("title_data", ""),self.styles["BiomarkerHeaderData"])
        box_category  = RoundedPill(biomarkers_data.get("title_pill", ""), colors.HexColor("#FFFCF5"), 8, 82, 18,8,colors.HexColor("#4E1D09"),colors.HexColor("#4E1D09"),0.4,FONT_INTER_REGULAR) 
        box_pill      = RoundedPill(biomarkers_data.get("pill", ""),pill_color, 8, 80, 18,8,colors.HexColor("#0C111D"))
        box_range     = biomarkers_data.get("footer", "")
        inner_left_stack=Table([
            [box_title],
            [Spacer(1,4)],
            [box_subtitle],
            [Spacer(1,8)],
            [box_category]
        ],colWidths=[None])
        inner_left_stack.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        combined_value_unit = Paragraph(
            f'<font name="{FONT_INTER_BOLD}" size="12" color="#003632">{biomarkers_data.get("value", "")}</font>'
            f'<font size="1"> </font>'  # This creates ~3pt space visually
            f'<font name="{FONT_INTER_REGULAR}" size="10" color="#667085">{biomarkers_data.get("suff", "")}</font>',
            self.styles["BiomarkerValue"]
        )
        upper_right_stack = Table([
            [combined_value_unit, Spacer(4, 1),box_pill]
        ], colWidths=[None, 4,None])
        upper_right_stack.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE") ,
        ]))

        combined_value_unit_ = Paragraph(
            f'<para alignment="right">'
            f'<font name="{FONT_INTER_REGULAR}" size="10" color="#667085">{box_range}</font>'
            f'<font size="1"> </font>'
            f'<font name="{FONT_INTER_REGULAR}" size="10" color="#667085">{biomarkers_data.get("suff", "")}</font>'
            f'</para>',
            self.styles["BiomarkerUnit"]
        )

        outer_left_stack = Table(
            [[inner_left_stack,upper_right_stack],
            ["",combined_value_unit_]],
            colWidths=[321,178],
        )
        outer_left_stack.setStyle(TableStyle([
            ("SPAN", (0, 0), (0, 1)), 
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1),0),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),   # Upper at top-right
            ("VALIGN", (1, 0), (1, 0), "TOP"),

            ("ALIGN", (1,-1), (1, -1), "RIGHT"),   # Bottom at bottom-right
            ("VALIGN", (1, -1), (1, -1), "BOTTOM")
        ]))
        outer_left_stack_ = Table(
            [[outer_left_stack]],
            colWidths=[A4[0]-64],
        )
        outer_left_stack_.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 16),
            ("RIGHTPADDING", (0, 0), (-1, -1), 16),
            ("TOPPADDING", (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))


        rounded_card = RoundedBox(
                width=A4[0]-64,
                height=None,
                content=outer_left_stack_,
                corner_radius=12,
                border_radius=0.25
            )

        section.append(header_data)
        section.append(Spacer(1,16))
        section.append(rounded_card)
        icon_path = os.path.join(svg_dir, "vitamin_b12.svg")  
        vitamin_b12_icon = self.svg_icon(icon_path, width=295, height=258)
        # img_path = os.path.join("staticfiles", "icons", "mineral_test_ratio_report.png")        
        # img = Image(img_path, width=558, height=531)
        section.append(Spacer(1,8))
        section.append(vitamin_b12_icon)
        final_table = Table([[item] for item in section], colWidths=[A4[0]])
        final_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))

        return final_table
        # return section

    def get_areas_of_concern(self, areas_of_concern: dict):
        section = []
        section.append(Indenter(left=32, right=32))
        title = areas_of_concern.get("title", "")
        title_data = areas_of_concern.get("title_data", "")

        cs = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        cs_data = Paragraph(title_data, self.styles["header_data_style"])
        section.append(cs_data)
        section.append(Spacer(1, 32))

        areas_of_concern_data_=areas_of_concern.get("areas_of_concern_data",[])

        for item in areas_of_concern_data_:
            pill_color     = item.get("pill_color", "#FFFFFF")
            box_title     = Paragraph(item.get("title", ""),self.styles["BiomarkerHeader"])
            box_subtitle  = Paragraph(item.get("title_data", ""),self.styles["BiomarkerHeaderData"])
            box_category  = item.get("title_pill", [])
            box_pill      = RoundedPill(item.get("pill", ""), pill_color, 8, 80, 18,8,colors.HexColor("#0C111D"))
            box_range     = item.get("footer", "")
           
            inner_box_list=[]
            col_widths=[]
            for inner_item in box_category:
                inner_box_category=RoundedPill(inner_item, colors.HexColor("#FFFCF5"), 8, 82, 18,8,colors.HexColor("#4E1D09"),colors.HexColor("#4E1D09"),0.4,FONT_INTER_REGULAR) 
                inner_box_list.append(inner_box_category)
                col_widths.append(82)
                inner_box_list.append(Spacer(width=4,height=0))
                col_widths.append(4)
            inner_box_table=Table(
                [inner_box_list],
                colWidths=col_widths
            )
            inner_box_table.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            inner_left_stack=Table([
                [box_title],
                [Spacer(1,4)],
                [box_subtitle],
                [Spacer(1,8)],
                [inner_box_table]
            ],colWidths=[None])
            inner_left_stack.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            combined_value_unit = Paragraph(
                f'<font name="{FONT_INTER_BOLD}" size="12" color="#003632">{item.get("value", "")}</font>'
                f'<font size="1"> </font>'  # This creates ~3pt space visually
                f'<font name="{FONT_INTER_REGULAR}" size="10" color="#667085">{item.get("suff", "")}</font>',
                self.styles["BiomarkerValue"]
            )
            upper_right_stack = Table([
                [combined_value_unit, Spacer(4, 1),box_pill]
            ], colWidths=[None, 4,None])
            upper_right_stack.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE") ,
            ]))

            combined_value_unit_ = Paragraph(
                f'<para alignment="right">'
                f'<font name="{FONT_INTER_REGULAR}" size="10" color="#667085">{box_range}</font>'
                f'<font size="1"> </font>'
                f'<font name="{FONT_INTER_REGULAR}" size="10" color="#667085">{item.get("suff", "")}</font>'
                f'</para>',
                self.styles["BiomarkerUnit"]
            )

            outer_left_stack = Table(
                [[inner_left_stack,upper_right_stack],
                ["",combined_value_unit_]],
                colWidths=[321,178],
            )
            outer_left_stack.setStyle(TableStyle([
                ("SPAN", (0, 0), (0, 1)), 
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1),0),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),   # Upper at top-right
                ("VALIGN", (1, 0), (1, 0), "TOP"),

                ("ALIGN", (1,-1), (1, -1), "RIGHT"),   # Bottom at bottom-right
                ("VALIGN", (1, -1), (1, -1), "BOTTOM")
            ]))
            outer_left_stack_ = Table(
                [[outer_left_stack]],
                colWidths=[A4[0]-64],
            )
            outer_left_stack_.setStyle(TableStyle([
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
            ]))


            rounded_card = RoundedBox(
                    width=A4[0]-64,
                    height=None,
                    content=outer_left_stack_,
                    corner_radius=12,
                    border_radius=0.25,
                    stroke_color="#999999"
                )
            section.append(rounded_card)
            section.append(Spacer(1,17))

        section.append(Indenter(left=-32, right=-32))
        return section

    def _create_diagnosis(self, diagnoses_data: list) -> list:
        # Create styled pills
        bullet = self.svg_icon(os.path.join("staticfiles","icons", "bullet.svg"), width=16, height=16)
        section=[]
        section.append(Indenter(left=32, right=32))

        title = diagnoses_data.get("title", "")

        cs = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))
        diagnoses_data_=diagnoses_data.get("diagnoses_data",[])
        section_=[]
        for val in diagnoses_data_:
            val_para=Paragraph(val,self.styles["bullet_after_text"])
            entry_table_ = Table([[bullet,Spacer(8,1),val_para]],colWidths=[16,8,None])
            entry_table_.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            entry_table = Table([[entry_table_]],colWidths=[240])
            entry_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                #("BOX",(0,0),(-1,-1),0.2,colors.HexColor("#000000"))
            ]))
            section_.append(RoundedBox(width=240, height=None, content=entry_table, corner_radius=16,border_radius=0.2))

        rows = []
        for i in range(0, len(section_), 2):
            item1 = section_[i]
            item2 = section_[i + 1] if i + 1 < len(section_) else Spacer(1, 4)

            row = [item1, Spacer(8, 1), item2]  # Spacer of 16pt between columns
            rows.append(row)

        # Create table
        table = Table(rows, colWidths=[240,8, 240], hAlign='LEFT')
        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        section.append(table)

        section.append(Indenter(left=-32, right=-32))

        return  section
    
    def _create_additional_diagnosis(self, additional_diagnoses_data: list) -> list:
        # Create styled pills
        bullet = self.svg_icon(os.path.join("staticfiles","icons", "bullet.svg"), width=24, height=24)
        section=[]
        section.append(Indenter(left=32, right=32))

        title = additional_diagnoses_data.get("title", "")

        cs = Paragraph(title, self.styles["TOCTitleStyle"])
        section.append(cs)
        section.append(Spacer(1, 16))

        additional_diagnoses_data_=additional_diagnoses_data.get("additional_diagnoses_data",{})
        section_=[]
        for val in additional_diagnoses_data_:
            name=val.get("name")
            location=val.get("location")
            location_pill= RoundedPill1(
                text=location,
                bg_color=colors.HexColor("#E6F4F3"),
                radius=46.622,
                width=None,
                height=None,
                font_size=8,
                text_color=colors.HexColor("#003632"),
                border_color=colors.HexColor("#26968D"),
                border_width=0.2,
                font_name=FONT_INTER_REGULAR,
            )
            val_para=Paragraph(name,self.styles["AdditionalDiagnostics"])
            
            entry_table_ = Table(
                [
                    [bullet,Spacer(1,16) ,val_para],
                    ["","",""],
                    ["",Spacer(1,16), location_pill]
                ],
                colWidths=[16,16, None]
            )

            entry_table_.setStyle(TableStyle([
                ("VALIGN", (0, 0), (0, 1), "MIDDLE"),     # Center bullet vertically across 2 rows
                ("SPAN", (0, 0), (0, 1)),                # Merge bullet cell vertically
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))


            entry_table = Table([[entry_table_]],colWidths=[240])
            entry_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                #("BOX",(0,0),(-1,-1),0.2,colors.HexColor("#000000"))
            ]))
            section_.append(RoundedBox(width=240, height=None, content=entry_table, corner_radius=16,border_radius=0.2))

        # Build rows of 2 pills each
        rows = []
        for i in range(0, len(section_), 2):
            item1 = section_[i]
            item2 = section_[i + 1] if i + 1 < len(section_) else Spacer(1, 4)

            row = [item1, Spacer(8, 1), item2]  # Spacer of 16pt between columns
            rows.append(row)

        # Create table
        table = Table(rows, colWidths=[240,8,240], hAlign='LEFT')
        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        section.append(table)

        section.append(Indenter(left=-32, right=-32))

        return section 

    def get_action_plan(self, action_plan: dict):
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = action_plan.get("header", "")
        action_plan_list_ = action_plan.get("action_plan_list", "")
        

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 10))

        for item in action_plan_list_:

            icon_path = os.path.join(svg_dir, "bullet_point_1.svg")
            icon = self.svg_icon(icon_path, width=16, height=16)

            section.append(SvgTitleRow(icon, Paragraph(item,self.styles["ActionPlanStyle"])))
            section.append(Spacer(1, 4))
        
        section.append(Indenter(left=-32, right=-32))

        return section
        
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
        
        page_width = A4[0]
        left_col_width = 126
        gap_between_columns = 16
        right_col_width = 322  # 64 = margins

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

            text_2 = Paragraph(
                name,
                self.styles["OptimizationPhasesStyle"]
            )
            left_stack.append(text_2)

            text_3 = Paragraph(
                f'({duration})',
                self.styles["OptimizationPhasesStyle"]
            )
            left_stack.append(text_3)
            # Use nested table to keep pill and paragraph side by side in the right column
            pill = RoundedPill(
                day,
                colors.HexColor("#CCE9E6"),
                8, 71, 18, 8,
                colors.HexColor("#003632"),
                colors.HexColor("#003632"),
                0.4,
                FONT_INTER_SEMI_BOLD
            )
            name_para = Paragraph(name, self.styles["BiomarkersStyle"])
            duration_para = Paragraph(f'<font color="#4DAEA6">{duration}</font>', self.styles["bullet_after_text"])
        
            name_width = stringWidth(name, self.styles["BiomarkersStyle"].fontName, self.styles["BiomarkersStyle"].fontSize)
            duration_width = stringWidth(duration, self.styles["bullet_after_text"].fontName, self.styles["bullet_after_text"].fontSize)
            # Combine pill and para horizontally using inner table
            if data:
                left_stack.append(VerticalLine(height=109))
                inner_table = Table(
                    [
                        [pill, Spacer(7, 1), name_para , Spacer(7, 1),duration_para],
                        [Paragraph(data, self.styles["eye_screening_desc_style"])]
                    ],
                    colWidths=[71, 7, name_width,7, 322-71-7-name_width-7]
                )
                inner_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("SPAN", (0, 1), (4, 1)), 
                ]))
            else:
                inner_table = Table(
                    [
                        [pill, Spacer(7, 1), name_para , Spacer(7, 1),duration_para]
                    ],
                    colWidths=[71, 7, name_width,7, None]
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
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ]))

            # Add to section
            section.append(final_table)
            section.append(Spacer(1, 8))  # Optional gap between entries

        section.append(Indenter(left=-32, right=-32))

        return section

    def get_morning_routine_protocol(self, morning_routine_protocol: dict):
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = morning_routine_protocol.get("header", "")
        title_data = morning_routine_protocol.get("header_data", "")
        routine_items = morning_routine_protocol.get("morning_routine_protocol_data", [])

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 8))

        # Section Subheading
        section.append(Paragraph(title_data, self.styles["RoutineStyle"]))
        section.append(Spacer(1, 8))

        pills = []

        for item in routine_items:
            pill_content = []

            # Icon and Title
            icon_path = os.path.join(svg_dir, "bullet_point_1.svg")
            icon = self.svg_icon(icon_path, width=16, height=16)

            title_text = item.get("title", "")
            title_para = Paragraph(title_text, self.styles["RoutineTitleStyle"])

            pill_content.append(SvgTitleRow(icon, title_para))
            pill_content.append(Spacer(1, 4))

            # Bullet descriptions
            title_data_list = item.get("title_data", [])
            for entry in title_data_list:
                desc = entry.get("description", "")
                pill_content.append(Paragraph(desc, self.styles["RoutineBulletStyle"], bulletText='•'))

                for subdesc in entry.get("sub_description", []):
                    pill_content.append(
                        Paragraph(f"- {subdesc}", self.styles["RoutineSubBulletStyle"])
                    )

            pills.append(pill_content)

        # Arrange 2 pills per row
        rows = []
        for i in range(0, len(pills), 2):
            row = pills[i:i+2]
            if len(row) < 2:
                row.append(Spacer(258, 0))  # fill empty cell if only 1 pill
            rows.append(row)

        # Create table for each row
        for row in rows:
            section.append(
                Table(
                    [row],
                    colWidths=[258, 258],
                    hAlign="LEFT",
                    style=TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ])
                )
            )
        section.append(Indenter(left=-32, right=-32))

        return section

    def get_cognitive_health_recommendations(self,health_recommendations: dict) -> list:
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = health_recommendations.get("header", "")
        health_recommendations_data_ = health_recommendations.get("health_recommendations_data", [])

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 32))

        for item in health_recommendations_data_:
            pill_content = []

            # Icon and Title
            icon_path = os.path.join(svg_dir, "bullet_point_1.svg")
            icon = self.svg_icon(icon_path, width=16, height=16)

            title_text = item.get("title", "")
            title_para = Paragraph(title_text, self.styles["RoutineTitleStyle"])

            pill_content.append(SvgTitleRow(icon, title_para))
            pill_content.append(Spacer(1, 8))

            # Bullet descriptions
            title_data_list = item.get("title_data", [])
            for entry in title_data_list:
                pill_content.append(Paragraph(entry, self.styles["RoutineBulletStyle"], bulletText='•'))

            section.append(KeepTogether(pill_content))
            section.append(Spacer(1, 16))
        section.append(Indenter(left=-32, right=-32))
        return section

    def get_lifestyle_recommendations(self, lifestyle_recommendations_data: dict):
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = lifestyle_recommendations_data.get("header", "")
        lifestyle_recommendations_data_ = lifestyle_recommendations_data.get("lifestyle_recommendations_data", [])

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 32))


        for item in lifestyle_recommendations_data_:
            pill_content = []

            # Icon and Title
            icon_path = os.path.join(svg_dir, "bullet_point_1.svg")
            icon = self.svg_icon(icon_path, width=16, height=16)

            title_text = item.get("title", "")
            title_para = Paragraph(title_text, self.styles["RoutineTitleStyle"])

            pill_content.append(SvgTitleRow(icon, title_para))
            pill_content.append(Spacer(1, 8))

            # Bullet descriptions
            title_data_list = item.get("title_data", [])
            for entry in title_data_list:
                desc = entry.get("description", "")
                
                if entry.get("video", ""):
                    desc += f' <a href="{entry.get("video", "")}"><u>Video</u></a>'
                if entry.get("app", ""):
                    desc += f', <a href="{entry.get("app", "")}"><u>App</u></a>'
                
                pill_content.append(Paragraph(desc, self.styles["RoutineBulletStyle"], bulletText='•'))

                for subdesc in entry.get("sub_description", []):
                    pill_content.append(
                        Paragraph(f"- {subdesc}", self.styles["RoutineSubBulletStyle"])
                    )

            section.append(KeepTogether(pill_content))
            section.append(Spacer(1,16))

        section.append(Indenter(left=-32, right=-32))

        return section
    
    def get_cardiovascular_recommendations(self, cardiovascular_recommendations: dict):
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = cardiovascular_recommendations.get("header", "")
        cardiovascular_recommendations_data_ = cardiovascular_recommendations.get("cardiovascular_recommendations_data", "")

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 32))


        for item in cardiovascular_recommendations_data_:
            pill_content = []

            # Icon and Title
            icon_path = os.path.join(svg_dir, "bullet_point_1.svg")
            icon = self.svg_icon(icon_path, width=16, height=16)

            title_text = item.get("title", "")
            title_para = Paragraph(title_text, self.styles["RoutineTitleStyle"])

            pill_content.append(SvgTitleRow(icon, title_para))
            pill_content.append(Spacer(1, 8))

            # Bullet descriptions
            title_data_list = item.get("title_data", [])
            for entry in title_data_list:
                if entry.get("description",""):
                    desc = entry.get("description", "")
                    pill_content.append(Paragraph(desc, self.styles["RoutineBulletStyle"], bulletText='•'))
                if entry.get("heading",""):
                    pill_content.append(Spacer(1, 16))
                    pill_content.append(Paragraph(entry.get("heading",""), self.styles["CardioVascularStyle"]))
                    
                for subdesc in entry.get("sub_description", []):
                    pill_content.append(
                        Paragraph(f"- {subdesc}", self.styles["RoutineSubBulletStyle"])
                    )

            section.append(KeepTogether(pill_content))
            
        
        section.append(Indenter(left=-32, right=-32))

        return section

    def get_start_suplements(self, start_suplements: dict):
        section = []

        section.append(Indenter(left=32, right=32))
        
        title = start_suplements.get("header", "")
        start_suplements_data_ = start_suplements.get("start_suplements_data", "")
        table_below_data = start_suplements.get("table_below_data", "")
        table_below_data_ = start_suplements.get("table_below_data_", "")

        # Section Heading
        section.append(Paragraph(title, self.styles["TOCTitleStyle"]))
        section.append(Spacer(1, 10))

        page_width = A4[0]
        left_col_width = 126
        gap_between_columns = 32
        right_col_width = page_width - 64 - left_col_width - gap_between_columns  # 64 = margins

        for item in start_suplements_data_:
            # Left stack (vertical)
            left_stack = []

            day = item.get("day", "00 day")
            supple_list = item.get("suple_list", [])

            icon_path = os.path.join(svg_dir, "supplement_icon.png")
            icon = Image(icon_path, width=16, height=16)
            left_stack.append(icon)
            left_stack.append(Spacer(1,8))

            text_1 = Paragraph(
                f'<font fontName={FONT_INTER_BOLD}>{day}</font>',
                self.styles["SSBUlletBelowStyle"]
            )
            left_stack.append(text_1)

            text_2 = Paragraph(
                f"{len(supple_list)} Supplement" if len(supple_list) == 1 else f"{len(supple_list)} Supplements",
                self.styles["SSBUlletBelowStyle"]
            )
            left_stack.append(text_2)

            # Use nested table to keep pill and paragraph side by side in the right column
            supplement_text = " + ".join(supple_list) + " Supplement" if supple_list else "Supplement"
            pill = RoundedPill(
                day,
                colors.HexColor("#CCE9E6"),
                8, 71, 18, 8,
                colors.HexColor("#003632"),
                colors.HexColor("#003632"),
                0.4,
                FONT_INTER_SEMI_BOLD
            )
            para = Paragraph(supplement_text, self.styles["BiomarkersStyle"])

            # Combine pill and para horizontally using inner table
            inner_table = Table(
                [[pill, Spacer(8, 1), para]],
                colWidths=[71, 8, right_col_width - 71 - 8]
            )
            inner_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))

            # Combine everything into the final row table with proper column spacing
            final_table = Table(
                [[left_stack, Spacer(gap_between_columns, 1), inner_table]],
                colWidths=[left_col_width, gap_between_columns, right_col_width]
            )

            final_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ]))

            # Add to section
            section.append(final_table)
            section.append(Spacer(1, 8))  # Optional gap between entries

        section.append(Paragraph(table_below_data,ParagraphStyle(
            name="BiomarkersStyle_Centered",
            parent=self.styles["BiomarkersStyle"],
            alignment=TA_CENTER
        )))
        section.append(Spacer(1, 17))
        section.append(Paragraph(table_below_data_,self.styles["eye_screening_desc_style"]))
        section.append(Indenter(left=-32, right=-32))

        return section

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
        
        lifestyle_trends=data.get("lifestyle_trends",{})
        if lifestyle_trends:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_lifestyle_trends(lifestyle_trends))
        
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

        body_composition=data.get("body_composition",{})
        if body_composition:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_body_composition(body_composition))
        
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
               
        resting_health=data.get("resting_health",{})
        if resting_health:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_resting_health(resting_health))
        
        fatty_acid=data.get("fatty_acid",{})
        if fatty_acid:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_fatty_acid(fatty_acid))
        
        digestive_health=data.get("digestive_health",{})
        if digestive_health:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestive_health(digestive_health))
        
        disease_susceptibility=data.get("disease_susceptibility",{})
        if disease_susceptibility:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestive_health(disease_susceptibility))
        
        digestion_potential=data.get("digestion_potential",{})
        if digestion_potential:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestion_potential(digestion_potential))
       
        lipid_digestion=data.get("lipid_digestion",{})
        if lipid_digestion:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestion_potential(lipid_digestion))
        
        short_chain_fatty_acid=data.get("short_chain_fatty_acid",{})
        if short_chain_fatty_acid:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestion_potential(short_chain_fatty_acid))
        
        gases=data.get("gases",{})
        if gases:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestion_potential(gases))
        
        neurotransmitters=data.get("neurotransmitters",{})
        if neurotransmitters:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestion_potential(neurotransmitters))
        
        vitamins=data.get("vitamins",{})
        if vitamins:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_digestion_potential(vitamins))
        
        understanding_biomarker=data.get("biomarkers_range",{})
        if understanding_biomarker:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.append(self.get_understanding_biomarker(understanding_biomarker))
        
        areas_of_concern=data.get("areas_of_concern",{})
        if areas_of_concern:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_areas_of_concern(areas_of_concern))
        
        diagnoses=data.get("diagnoses",{})
        if diagnoses:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self._create_diagnosis(diagnoses))

        additional_diagnoses=data.get("additional_diagnoses",{})
        if additional_diagnoses:
            story.append(Spacer(1, 24))
            story.extend(self._create_additional_diagnosis(additional_diagnoses))

        action_plan=data.get("action_plan",{})
        if action_plan:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_action_plan(action_plan))

        optimization_phases=data.get("optimization_phases",{})
        if optimization_phases:
            story.append(Spacer(1, 16))
            story.extend(self.get_optimization_phases(optimization_phases))

        morning_routine_protocol=data.get("morning_routine_protocol",{})
        if morning_routine_protocol:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_morning_routine_protocol(morning_routine_protocol))
        
        cognitive_health_recommendations=data.get("cognitive_health_recommendations",{})
        if cognitive_health_recommendations:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_cognitive_health_recommendations(cognitive_health_recommendations))
        
        lifestyle_recommendations=data.get("lifestyle_recommendations",{})
        if lifestyle_recommendations:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_lifestyle_recommendations(lifestyle_recommendations))

        cardiovascular_recommendations=data.get("cardiovascular_recommendations",{})
        if cardiovascular_recommendations:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_cardiovascular_recommendations(cardiovascular_recommendations))
    
        start_suplements=data.get("start_suplements",{})
        if start_suplements:
            story.append(PageBreak())
            story.append(Spacer(1, 8))
            story.extend(self.get_start_suplements(start_suplements))
        
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

    image_frame = Frame(
        x1=0,
        y1=0,
        width=A4[0],
        height=A4[1],
        id='image',
        leftPadding=0,
        bottomPadding=0,
        rightPadding=0,
        topPadding=0,
    )

    doc.addPageTemplates([
        PageTemplate(id='main', frames=[frame], onPage=renderer.draw_header, onPageEnd=renderer.draw_footer),
        PageTemplate(id='image', frames=[image_frame])
    ])
    flowables = template.generate(data)  
    flowables.append(NextPageTemplate('image'))

    # Full-page image
    img_path = os.path.join(svg_dir, "final_page.png")
    full_page_image = Image(img_path, width=A4[0], height=A4[1])
    full_page_image.hAlign = 'CENTER'
    flowables.append(full_page_image)
    doc.build(flowables, canvasmaker=NumberedCanvas)
    with open("output_from_buffer_stash.pdf", "wb") as f:
        f.write(buffer.getvalue())
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "inline; filename=styled_output.pdf"
    })




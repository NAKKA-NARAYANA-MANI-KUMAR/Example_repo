import io
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer,Indenter,TableStyle,Table,Flowable,Image,PageBreak,NextPageTemplate,
    KeepTogether
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from svglib.svglib import svg2rlg
from reportlab.graphics.shapes import Drawing,Rect, String, Line,Circle, Path, Group
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

# === Constants ===
PAGE_WIDTH, PAGE_HEIGHT = A4
HEADER_HEIGHT = 48
FOOTER_HEIGHT = 80

FONT_INTER_SEMI_BOLD = "Inter-SemiBold"
FONT_INTER_REGULAR = "Inter-Regular"
FONT_INTER_BOLD = "Inter-Bold"
FONT_RALEWAY_BOLD="Raleway-Bold"
FONT_INTER_LIGHT="Inter-Light"
FONT_INTER_MEDIUM="Inter-Medium"
FONT_INTER_THIN="Inter-Thin"
FONT_RALEWAY_REGULAR="Raleway-Regular"
FONT_RALEWAY_LIGHT = "Raleway-Light"
FONT_RALEWAY_THIN="Raleway-Thin"
FONT_RALEWAY_MEDIUM="Raleway-Medium"

FONT_SIZE_MEDIUM = 12
FONT_SIZE_SMALL = 10

PMX_GREEN = colors.HexColor("#00625B")
LIGHT_GREEN = colors.HexColor("#DFF9BA")

# === Register Fonts ===
def register_fonts():
    fonts = {
        FONT_INTER_REGULAR: "staticfiles/fonts/inter/Inter-Regular.ttf",
        FONT_INTER_BOLD: "staticfiles/fonts/inter/Inter-Bold.ttf",
        FONT_INTER_SEMI_BOLD: "staticfiles/fonts/inter/Inter-SemiBold.ttf",
        FONT_RALEWAY_BOLD:"staticfiles/fonts/Raleway-Bold.ttf",
        FONT_INTER_LIGHT: "staticfiles/fonts/inter/Inter-Light.ttf",
        FONT_INTER_MEDIUM: "staticfiles/fonts/inter/Inter-Medium.ttf",
        FONT_RALEWAY_REGULAR: "staticfiles/fonts/Raleway-Regular.ttf",
        FONT_RALEWAY_LIGHT: "staticfiles/fonts/Raleway-Light.ttf",
        FONT_INTER_THIN :"staticfiles/fonts/inter/Inter-Thin.ttf",
        FONT_RALEWAY_THIN :"staticfiles/fonts/Raleway-Thin.ttf",
        FONT_RALEWAY_MEDIUM: "staticfiles/fonts/Raleway-Medium.ttf"

    }
    for name, path in fonts.items():
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))
        else:
            print(f"Font file not found: {path}")

register_fonts()

metrics={
    "CARDIAC HEALTH": {
      "image": "heartbeat.svg",
      "width": 48,
      "height": 48
    },
    "METABOLIC HEALTH": {
      "image": "metabolic_health.svg",
      "width": 53,
      "height": 53
    },
    "VASCULAR HEALTH": {
      "image": "vascular_health.svg",
      "width": 52,
      "height": 52
    },
    "Gut and Immune Health": {
      "image": "gut_immune.svg",
      "width": 48,
      "height": 48
    },
    "Kidney and Liver Health": {
      "image": "kidney_liver.svg",
      "width": 46,
      "height": 46
    },
    "Neuro Health": {
      "image": "neuro_health.svg",
      "width": 48,
      "height": 48
    },
    "Mood Disorders": {
      "image": "mood_disorders.svg",
      "width": 50,
      "height": 50
    },
    "MUSCLE AND BONE HEALTH": {
      "image": "muscle_bone.svg",
      "width": 43.7,
      "height": 51.49
    },
    "Aging and Longevity": {
      "image": "aging_longevity.svg",
      "width": 55,
      "height": 55
    },
    "Eye Health": {
      "image": "eye_health.svg",
      "width": 55,
      "height": 46
    },
    "Nutrition": {
      "image": "nutrition.svg",
      "width": 53,
      "height": 53
    },
    "Methylation Genes": {
      "image": "methylation.svg",
      "width": 50,
      "height": 50
    },
    "Liver Detox Phase 1": {
      "image": "liver_detox.svg",
      "width": 52,
      "height": 52
    },
    "Liver Detox Phase 2": {
      "image": "liver_detox.svg",
      "width": 52,
      "height": 52
    },
    "Hereditary Cancer": {
      "image": "hereditary_cancer.svg",
      "width": 52,
      "height": 52
    }
  }

# === Styles ===
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    'titlestyle',
    fontName=FONT_INTER_BOLD,               # Make sure the font is registered
    fontSize=12,
    leading=14,                       # Approximate line-height
    textColor=colors.HexColor("#DFF9BA"),
    spaceAfter=0,                    # Optional: space after paragraph
    spaceBefore=0,                   # Optional: space before paragraph
    wordSpacing=0.48,                # letter-spacing equivalent
    alignment=0,                     # 0=left, 1=center, 2=right, 4=justify
))
styles.add(ParagraphStyle(
    "titledatastyle",
    fontName=FONT_INTER_REGULAR,         # Make sure the font is registered
    fontSize=8,                 # 8 px → 8 pt (same)
    leading=10,                 # line-height (slightly above 8)
    textColor=colors.HexColor("#DFF9BA"),
    spaceAfter=0,               # optional spacing
    spaceBefore=0,              # optional spacing
))
styles.add(ParagraphStyle(
    "HeaderStyle",
    fontName=FONT_RALEWAY_BOLD,         # You must register this font
    fontSize=12,
    leading=14,                      # Approximate line height (adjustable)
    textColor=colors.HexColor("#152022"),
    spaceAfter=0,
    spaceBefore=0,
))
styles.add(ParagraphStyle(
    "HeaderDataStyle",
    fontName=FONT_INTER_LIGHT,               # Matches the registered font
    fontSize=8,
    leading=10,                           # Slightly above font size, adjust if needed
    textColor=colors.HexColor("#152022"),
    spaceAfter=0,
    spaceBefore=0,
))
styles.add(ParagraphStyle(
    "GenesAnalyzedStyle",
    fontName=FONT_INTER_MEDIUM,                    
    fontSize=10,                                
    leading=12,                                 
    textColor=colors.HexColor('#152022'),       
    spaceBefore=0,
    spaceAfter=0
)                      
)

class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        self.allowSplitting = 0

class NumberedCanvas(Canvas):
    def __init__(self, *args, footer_label="", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.footer_label = footer_label

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(total_pages)
            self.draw_footer_label_with_icon()
            super().showPage()
        super().save()

    def draw_page_number(self, total_pages):
        page_number = self.getPageNumber()
        if page_number <= 1:
            return ""
        text = f"Page {page_number:02d} - {total_pages:02d}"
        font = FONT_INTER_REGULAR
        size = 8
        text_width = stringWidth(text, font, size)
        self.setFont(font, size)
        self.setFillColor(colors.HexColor("#949599"))
        self.drawString(PAGE_WIDTH - 32 - text_width, 20, text)

    def draw_footer_label_with_icon(self):
        if not self.footer_label:
            return
        page_number = self.getPageNumber()
        if page_number <= 1:
            return

        x = 57
        y = 20
        font = FONT_INTER_REGULAR
        size = 8
        label = self.footer_label
        label_width = stringWidth(label, font, size)

        # Draw the label
        self.setFont(font, size)
        self.setFillColor(colors.HexColor("#949599"))
        self.drawString(x, y, label)

        # Draw the image after the label
        try:
            svg_path = os.path.join("staticfiles", "icons", "pmx_green_logo.svg")
            drawing = svg2rlg(svg_path)

            # Get scale factors
            target_width = 21
            target_height = 10
            scale_x = target_width / drawing.width
            scale_y = target_height / drawing.height

            # Apply scaling (without altering original width/height)
            drawing.scale(scale_x, scale_y)

            # Draw the scaled SVG right after the label
            renderPDF.draw(drawing, self, x + label_width + 4, y - 1)
        except Exception as e:
            print(f"Failed to render SVG: {e}")

class ImageWithOverlaySVGAndText(Flowable):
    def __init__(self, main_image_path, svg_path, width=400, height=300,
                 svg_pos=(53, 162), svg_size=(181, 84), text="PMX0000",user_name=""):
        super().__init__()
        self.main_image_path = main_image_path
        self.svg_path = svg_path
        self.width = width                  # main image width
        self.height = height                # main image height
        self.svg_pos = svg_pos              # (x, y from top)
        self.svg_size = svg_size            # (width, height)
        self.text = text
        self.user_name=user_name

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        # Draw main image
        try:
            main_img = ImageReader(self.main_image_path)
            self.canv.drawImage(main_img, 0, 0, width=self.width, height=self.height, mask='auto')
        except Exception as e:
            print(f"Failed to draw main image: {e}")

        # Draw scaled SVG overlay
        try:
            drawing = svg2rlg(self.svg_path)
            scale_x = self.svg_size[0] / drawing.width
            scale_y = self.svg_size[1] / drawing.height

            self.canv.saveState()
            self.canv.translate(53, A4[1]-162)
            self.canv.scale(scale_x, scale_y)
            renderPDF.draw(drawing, self.canv, 0, 0)
            self.canv.restoreState()
        except Exception as e:
            print(f"Failed to render SVG: {e}")

        try:
            # Load PNG image
            png_path = os.path.join("staticfiles", "icons", "pmx_x_white.png")
            img = ImageReader(png_path)

            # Set position and size (x=53, y=top-162, width=181, height=84)
            x = 53
            y = A4[1] - 728  # Y coordinate from bottom
            width = 16
            height = 18

            # Draw the image
            self.canv.drawImage(img, x, y, width=width, height=height, mask='auto')
        except Exception as e:
            print(f"Failed to render PNG: {e}")

        try:
            # Optional: Draw text BELOW the image
            self.canv.setFillColorRGB(1, 1, 1)  # White color
            self.canv.setFont(FONT_RALEWAY_THIN, 95.75)  # Approx. 95.75 px
            self.canv.drawString(49, A4[1]-254, "Genome")
            self.canv.setFont(FONT_INTER_THIN, 95.75)  # Approx. 95.75 px
            self.canv.drawString(49, A4[1]-366, "360 Report")  # Position below image
            self.canv.setFont(FONT_INTER_REGULAR, 16)  # Approx. 95.75 px
            self.canv.drawString(76, A4[1]-726, f"ID - {self.text}")
            self.canv.setFont(FONT_RALEWAY_MEDIUM, 30)  # Approx. 95.75 px
            self.canv.drawString(52, A4[1]-756, self.user_name)
        except Exception as e:
            print(f"Failed to render text: {e}")

class FixedSizeDrawing(Flowable):
    def __init__(self, drawing, width, height):
        super().__init__()
        self.drawing = drawing
        self.width = width
        self.height = height

        # Compute scale factor
        self._scale_x = width / (drawing.width or 1)
        self._scale_y = height / (drawing.height or 1)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.translate(0, 0)
        self.canv.scale(self._scale_x, self._scale_y)
        renderPDF.draw(self.drawing, self.canv, 0, 0)
        self.canv.restoreState()

class ThrivePageRenderer:
    def __init__(self, template):
        self.template = template

    def draw_header(self, canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT_INTER_REGULAR, FONT_SIZE_MEDIUM)
        canvas.setFillColor(PMX_GREEN)
        canvas.drawString(30, PAGE_HEIGHT - 30, "Thrive Limitless")
        canvas.restoreState()

    def draw_footer(self, canvas, doc):
        if doc.page == 1:
            return
        canvas.saveState()
        canvas.setFont(FONT_INTER_REGULAR, FONT_SIZE_SMALL)
        canvas.setFillColor(PMX_GREEN)
        canvas.drawString(30, 30, "PMX Health")
        canvas.restoreState()

class HorizontalLine(Flowable):
    def __init__(self, width=40, thickness=0.2, color=None):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.height = thickness  # Needed for Flowable layout engine
        self.color = color

    def draw(self):
        if self.color:
            self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)

class RoundedTopRightTable(Flowable):
    def __init__(self, data, colWidths=[303, 154,55], height=60, radius=25):
        super().__init__()
        self.data = data
        self.colWidths = colWidths
        self.width = A4[0]-79
        self.height = height
        self.radius = radius

    def draw(self):
        c = self.canv
        x, y = 0, 0
        w, h, r = self.width, self.height, self.radius

        # Save canvas state
        c.saveState()

        # Draw background with top-right rounded corner
        c.setFillColor(colors.HexColor("#003E39"))
        path = c.beginPath()
        path.moveTo(x, y)                     # Bottom-left
        path.lineTo(x, y + h)                 # Top-left
        path.lineTo(x + w - r, y + h)         # Before curve
        path.arcTo(x + w - 2 * r, y + h - 2 * r, x + w, y + h, startAng=90, extent=-90)
        path.lineTo(x + w, y)                 # Bottom-right
        path.lineTo(x, y)                     # Back to start
        path.close()
        c.drawPath(path, fill=1, stroke=0)

        # Create the table (transparent background)
        table = Table(self.data, colWidths=self.colWidths)
        table.setStyle(TableStyle([
            
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),0),
            ("BOTTOMPADDING",(0,0),(-1,-1),0),
            ("RIGHTPADDING",(0,0),(-1,-1),0),
            ("LEFTPADDING",(0,0),(-1,-1),0),
            ("LEFTPADDING",(0,0),(0,-1),13),
            ("RIGHTPADDING",(-1,0),(-1,-1),13)
        ]))

        # Draw table
        table.wrapOn(c, self.width, self.height)
        table.drawOn(c, x, y)

        c.restoreState()

def hex_to_rgb(hex_color, alpha=1.0):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return colors.Color(r / 255, g / 255, b / 255, alpha=alpha)

def draw_person_icon(color="#488F31", scale=1.5):
    g = Group()

    head_radius = 2 * scale
    head_center_x = 5 * scale
    head_center_y = 8.2 * scale
    head = Circle(head_center_x, head_center_y, head_radius,
                  fillColor=HexColor(color), strokeColor=None)
    g.add(head)

    body = Path(fillColor=HexColor(color), strokeColor=None)

    def pt(xp, yp):
        return xp * scale, (6 - yp) * scale

    body.moveTo(*pt(3.72534, 6.0866))
    body.lineTo(*pt(1.24721, 1.37812))
    body.curveTo(*pt(0.658151, 0.26094),
                 *pt(1.84846, -0.95375),
                 *pt(2.97784, -0.38906))
    body.lineTo(*pt(4.29409, 0.26906))
    body.curveTo(*pt(4.65971, 0.45187),
                 *pt(5.09034, 0.45187),
                 *pt(5.45596, 0.26906))
    body.lineTo(*pt(6.77221, -0.38906))
    body.curveTo(*pt(7.90159, -0.95375),
                 *pt(9.08784, 0.26094),
                 *pt(8.50284, 1.37812))
    body.lineTo(*pt(6.02471, 6.0866))
    body.curveTo(*pt(5.53721, 7.01281),
                 *pt(4.21284, 7.01281),
                 *pt(3.72534, 6.0866))
    body.closePath()

    g.add(body)

    drawing = Drawing(16 * scale, 20 * scale)
    drawing.add(g)
    return drawing

def draw_status_bar(c, x, y, active_label, sections):
    padding = 2
    inactive_width = 58
    inactive_height = 20
    active_width = 85
    active_height = 22
    radius = inactive_height / 2

    total_width = 0
    widths = []
    for label, _ in sections:
        w = active_width if label == active_label else inactive_width
        widths.append(w)
        total_width += w + padding
    total_width -= padding

    current_x = x
    for i, (label, hex_color) in enumerate(sections):
        is_active = (label == active_label)
        width = active_width if is_active else inactive_width
        height = active_height if is_active else inactive_height
        corner_radius = height / 2 if (i == 0 or i == len(sections) - 1) else 0

        fill_color = hex_to_rgb(hex_color, alpha=1.0 if is_active else 0.4)
        c.setFillColor(fill_color)

        if corner_radius > 0:
            path = c.beginPath()
            if i == 0:
                path.moveTo(current_x + corner_radius, y)
                path.lineTo(current_x + width, y)
                path.lineTo(current_x + width, y + height)
                path.lineTo(current_x + corner_radius, y + height)
                path.arcTo(current_x, y, current_x + 2*corner_radius, y + height, startAng=90, extent=180)
                path.close()
            elif i == len(sections) - 1:
                path.moveTo(current_x, y)
                path.lineTo(current_x + width - corner_radius, y)
                path.arcTo(current_x + width - 2*corner_radius, y, current_x + width, y + height, startAng=270, extent=180)
                path.lineTo(current_x, y + height)
                path.close()
            c.drawPath(path, fill=1, stroke=0)
        else:
            c.rect(current_x, y, width, height, fill=1, stroke=0)

        c.setFillColor(colors.white)
        c.setFont(FONT_RALEWAY_BOLD, 10)
        c.drawCentredString(current_x + width / 2, y + height / 2 - 3, label)

        # Draw person icon above active label
        if is_active:
            person = draw_person_icon(color=hex_color, scale=1.5)
            icon_width = 16 * 1.5
            icon_height = 20 * 1.5
            icon_x = current_x + (width - icon_width) / 2
            icon_y = y + height + 6
            renderPDF.draw(person, c, icon_x, icon_y)

        current_x += width + padding

class StatusBarFlowable(Flowable):
    def __init__(self, active_label, sections, width=None, height=60):
        super().__init__()
        self.active_label = active_label
        self.sections = sections
        self.height = height
        self.width = width or self.calculate_total_width()

    def calculate_total_width(self):
        padding = 2
        inactive_width = 58
        active_width = 85
        total = 0
        for label, _ in self.sections:
            w = active_width if label == self.active_label else inactive_width
            total += w + padding
        return total - padding

    def draw(self):
        draw_status_bar(self.canv, 0, 0, self.active_label, self.sections)

class CustomTextBoxFlowable(Flowable):
    def __init__(self, text, font_size=8, letter_spacing=1.44, padding=4, 
                 font_name=FONT_RALEWAY_BOLD, font_color='#003E39', 
                 bg_color=colors.Color(239/255, 239/255, 239/255, alpha=0.6),
                 border_radius=2):
        Flowable.__init__(self)
        self.text = text
        self.font_size = font_size
        self.letter_spacing = letter_spacing
        self.padding = padding
        self.font_name = font_name
        self.font_color = colors.HexColor(font_color)
        self.bg_color = bg_color
        self.border_radius = border_radius

        # Calculate width and height during init
        self.text_width = self._calculate_text_width()
        self.width = self.text_width + 2 * self.padding
        self.height = self.font_size + 2 * self.padding

    def _calculate_text_width(self):
        return sum(stringWidth(c, self.font_name, self.font_size) + self.letter_spacing for c in self.text) - self.letter_spacing

    def draw(self):
        c = self.canv
        x = 0
        y = 0

        # Draw rounded background rectangle
        c.setFillColor(self.bg_color)
        c.roundRect(x, y, self.width, self.height, radius=self.border_radius, stroke=0, fill=1)

        # Draw the text manually with letter spacing
        c.setFont(self.font_name, self.font_size)
        c.setFillColor(self.font_color)

        cursor_x = x + self.padding
        cursor_y = y + self.padding

        for char in self.text:
            c.drawString(cursor_x, cursor_y, char)
            cursor_x += stringWidth(char, self.font_name, self.font_size) + self.letter_spacing

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
    def __init__(self, buffer):
        self.buffer = buffer
        self.styles = styles

    def draw_diagonal_line_block(self,width=154, height=80):
        drawing = Drawing(width, height)

        # Define the stroke color
        line_color = colors.HexColor("#DFF9BA")
        line_opacity = 0.2
    
        # Create diagonal lines (from the SVG you posted)
        lines = [
            Line(47.5851, 21.721, 86.5851, -36.279),   # Line 1
            Line(102.585, 115.721, 141.585, 57.721),   # Line 2
            Line(34.5851, 31.721, 73.5851, -26.279),   # Line 3
            Line(89.5851, 125.721, 128.585, 67.721),   # Line 4
        ]

        # Apply color and opacity
        for line in lines:
            line.strokeColor = line_color
            line.strokeWidth = 1
            line.strokeOpacity = line_opacity  # This property works in renderPDF context
            drawing.add(line)
        drawing.transform = [1, 0, 0, -1, 0, height]
        return drawing

    def svg_icon(self, path, width=12, height=12):
        try:
            drawing = svg2rlg(path)
            if drawing is None:
                raise FileNotFoundError(f"SVG file '{path}' could not be loaded or is invalid.")
        except Exception as e:
            print(f"[svg_icon] Error loading SVG: {e}")
            return Drawing(width, height)

        return FixedSizeDrawing(drawing, width, height)

    def get_heading(self, user_profile_card: str):
        title = user_profile_card.get("title", "No Title Provided")
        content = user_profile_card.get("content", "No content available.")
        title_para= Paragraph(title, self.styles['titlestyle'])
        content_para=Paragraph(content, self.styles['titledatastyle'])
        merged_para = Paragraph(
            f"<font name='{FONT_INTER_BOLD}' size='12'>{title}</font><br/><br/>"
            f"<font name='{FONT_INTER_REGULAR}' size='8'>{content}</font>",
            styles["titledatastyle"]  # This provides spacing and alignment
        )

        mask_group = self.draw_diagonal_line_block(width=154, height=80)

        heartbeat_path = os.path.join("staticfiles", "icons", metrics[title].get("image","heartbeat.svg"))
        heartbeat = self.svg_icon(heartbeat_path, width=metrics[title].get("width",55), height=metrics[title].get("height",55))
        data = [[merged_para,mask_group,heartbeat]]

        rounded_table = RoundedTopRightTable(data, height=80, radius=25)
        
        return rounded_table

    def get_table_data(self,main_data:list,sections:list):
        header=main_data.get("header","")
        header_data=main_data.get("header_data","")
        active_label=main_data.get("range","Low")
        header_para=Paragraph(header,styles["HeaderStyle"])
        header_data_para=Paragraph(header_data,styles["HeaderDataStyle"])
        line=HorizontalLine(width=40, thickness=0.2, color=colors.HexColor("#949599"))
        status_bar=StatusBarFlowable(active_label=active_label, sections=sections)

        table_ = Table([
            [line, header_para, "", status_bar],
            ["", header_data_para, "", ""]
        ], colWidths=[44, 247, 8, A4[0] - 44 - 247 - 8])

        table_.setStyle(TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 36),
            ("VALIGN", (0,0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("SPAN", (2, 0), (2, 1)),
            ("SPAN", (3, 0), (3, 1)),
            # ("GRID", (0, 0), (-1, -1), 0.25, colors.red)
        ]))

        return table_
    
    def get_interpretation_analyzed(self,data:dict):
        interpretation=data.get("interpretation","")
        genes_analyzed=data.get("genes_analyzed","")

        genes_analyzed_ = CustomTextBoxFlowable("GENES ANALYSED")
        interpretation_ = CustomTextBoxFlowable("INTERPRETATION")

        interpretation_para=Paragraph(interpretation,styles["GenesAnalyzedStyle"])
        genes_analyzed_para=Paragraph(genes_analyzed,styles["GenesAnalyzedStyle"])
        if interpretation and genes_analyzed:
            
            table_ = Table([
                [genes_analyzed_,"", "", interpretation_],
                [genes_analyzed_para, "", "", interpretation_para]
            ], colWidths=[240,8, 8,227])

            table_.setStyle(TableStyle([
                ("BOTTOMPADDING", (0, 1), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEAFTER", (1,0), (1, -1), 0.01, colors.HexColor("#949599")),
                ("VALIGN", (0,0), (-1, -1), "TOP"),
                # ("BOX", (0, 0), (-1, -1), 0.01,colors.HexColor("#949599") , None, None, "round"),
            ]))
        elif interpretation:
            table_ = Table([
                [interpretation_,"", "", ""],
                [interpretation_para, "", "", ""]
            ], colWidths=[227,8, 8,240])

            table_.setStyle(TableStyle([
                ("BOTTOMPADDING", (0, 1), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0,0), (-1, -1), "TOP"),
            ]))
        tablee=Table([[table_]],colWidths=[A4[0]-80])
        tablee.setStyle(TableStyle([
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ("BOX", (0, 0), (-1, -1), 0.01,colors.HexColor("#949599") , None, None, "round"),
        ]))
        return tablee
    
    def generate_section(self,data_card,sections):
        story=[]
        main_data=data_card.get("data",[])
        story.append(Indenter(left=44, right=35))
        story.append(self.get_heading(data_card))
        story.append(Indenter(left=-44, right=-35))
        story.append(Spacer(1,24))
        if main_data:
            for item in main_data:
                table_data=self.get_table_data(item,sections)
                interpretation_analyzed=self.get_interpretation_analyzed(item)
                # story.append(table_data)
                # story.append(Spacer(1,8))
                # story.append(interpretation_analyzed)
                wrapped = Table([
                    [table_data],
                    [Spacer(1, 8)],
                    [interpretation_analyzed]
                ], colWidths=[PAGE_WIDTH])
                wrapped.setStyle(TableStyle([
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),

                ]))
                story.append(wrapped)
                story.append(Spacer(1,16))
        return story
    
    def generate(self, data: dict):
        story = []
        cardiac_health_data = data.get("cardiac_health_data", {})
        section = [
                ("Low", "#488F31"),
                ("Mild", "#F49E5C"),
                ("Moderate", "#DE425B")
        ]
        sections = [
                ("Low", "#488F31"),
                ("Mild", "#F49E5C"),
                ("Moderate", "#DE425B"),
                ("High", "#912018")
        ]
        if cardiac_health_data:
            cardiac_health=self.generate_section(cardiac_health_data,section)
            story.extend(cardiac_health)
        metabolic_health_data = data.get("metabolic_health_data", {})
        if metabolic_health_data:
            story.append(PageBreak())
            metabolic_health=self.generate_section(metabolic_health_data,sections)
            story.extend(metabolic_health)
        
        vascular_health_data=data.get("vascular_health_data", {})
        if vascular_health_data:
            story.append(PageBreak())
            vascular_health=self.generate_section(vascular_health_data,sections)
            story.extend(vascular_health)
        
        gut_immune_health_data=data.get("gut_immune_health_data", {})
        if gut_immune_health_data:
            story.append(PageBreak())
            gut_immune_health=self.generate_section(gut_immune_health_data,sections)
            story.extend(gut_immune_health)
        
        kidney_liver_health_data=data.get("kidney_liver_health_data", {})
        if kidney_liver_health_data:
            story.append(PageBreak())
            kidney_liver_health=self.generate_section(kidney_liver_health_data,sections)
            story.extend(kidney_liver_health)
        
        neuro_health_data=data.get("neuro_health_data", {})
        if neuro_health_data:
            story.append(PageBreak())
            neuro_health=self.generate_section(neuro_health_data,sections)
            story.extend(neuro_health)
        
        mood_disorders_data=data.get("mood_disorders_data", {})
        if mood_disorders_data:
            story.append(PageBreak())
            mood_disorders=self.generate_section(mood_disorders_data,sections)
            story.extend(mood_disorders)
         
        muscle_bone_health_data=data.get("muscle_bone_health_data", {})
        if muscle_bone_health_data:
            story.append(PageBreak())
            muscle_bone_health=self.generate_section(muscle_bone_health_data,sections)
            story.extend(muscle_bone_health)
        
        aging_longevity_data=data.get("aging_longevity_data", {})
        if aging_longevity_data:
            story.append(PageBreak())
            aging_longevity=self.generate_section(aging_longevity_data,sections)
            story.extend(aging_longevity)
        
        eye_health_data=data.get("eye_health_data", {})
        if eye_health_data:
            story.append(PageBreak())
            eye_health=self.generate_section(eye_health_data,sections)
            story.extend(eye_health)
        
        nutrition_data=data.get("nutrition_data", {})
        if nutrition_data:
            story.append(PageBreak())
            nutrition=self.generate_section(nutrition_data,sections)
            story.extend(nutrition)

         
        methylation_data=data.get("methylation_data", {})
        if methylation_data:
            story.append(PageBreak())
            methylation=self.generate_section(methylation_data,sections)
            story.extend(methylation)
        sections__ = [
                ("Poor", "#B42318"),
                ("Normal", "#488F31"),
                ("Intermediate", "#F79009"),
                ("Rapid", "#912018")
        ]
        liver_detox_phase1=data.get("liver_detox_phase1", {})
        if liver_detox_phase1:
            story.append(PageBreak())
            liver_detox_phase1_=self.generate_section(liver_detox_phase1,sections__)
            story.extend(liver_detox_phase1_)
        
        liver_detox_phase2=data.get("liver_detox_phase2", {})
        if liver_detox_phase2:
            story.append(PageBreak())
            liver_detox_phase2_=self.generate_section(liver_detox_phase2,sections__)
            story.extend(liver_detox_phase2_)

        hereditary_cancer_data=data.get("hereditary_cancer_data", {})
        if hereditary_cancer_data:
            story.append(PageBreak())
            hereditary_cancer=self.generate_section(hereditary_cancer_data,sections)
            story.extend(hereditary_cancer)
        
        return story

# === FastAPI App ===
app = FastAPI()

@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    data = await request.json()
    buffer = io.BytesIO()

    template = ThriveRoadmapTemplate(buffer)
    renderer = ThrivePageRenderer(template)

    # PageTemplate for full-page image (page 1 only)
    full_page_frame = Frame(
        x1=0, y1=0,
        width=PAGE_WIDTH,
        height=PAGE_HEIGHT,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id='fullpage'
    )

    # PageTemplate for all other pages (with header/footer)
    main_frame = Frame(
        x1=0, y1=FOOTER_HEIGHT,
        width=PAGE_WIDTH,
        height=PAGE_HEIGHT - HEADER_HEIGHT - FOOTER_HEIGHT,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id='main'
    )

    doc = MyDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0,
        rightMargin=0,
        topMargin=HEADER_HEIGHT,
        bottomMargin=FOOTER_HEIGHT
    )

    # Add templates
    doc.addPageTemplates([
        PageTemplate(id='fullpage', frames=[full_page_frame]),
        PageTemplate(id='main', frames=[main_frame])
    ])

    story = []
    id=data.get("user_id","")
    user_name=data.get("user_name","")
    story.append(ImageWithOverlaySVGAndText(
        main_image_path="staticfiles/icons/genome_page.png",
        svg_path="staticfiles/icons/pmx_logo.svg",
        width=PAGE_WIDTH,
        height=PAGE_HEIGHT,
        svg_pos=(53, 162),
        svg_size=(181, 84),
        text=id,
        user_name=user_name
    ))


    # === Tell ReportLab to switch to 'main' template from here on ===
    story.append(NextPageTemplate("main"))

    # === Page 2 onward ===
    story.extend(template.generate(data))

    user_name = data.get("user_name", "")
    doc.build(story, canvasmaker=lambda *args, **kwargs: NumberedCanvas(*args, footer_label=user_name, **kwargs))

    with open("genome.pdf", "wb") as f:
        f.write(buffer.getvalue())

    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "inline; filename=styled_output.pdf"
    })

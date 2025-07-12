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
    Image, Flowable, KeepTogether, PageBreak, SimpleDocTemplate
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
from reportlab.graphics.shapes import Drawing

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


class ThriveRoadmapTemplate:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.base_path = Path("staticfiles/icons")
        self.init_styles()

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
            "box_footer_style",
            fontName=FONT_INTER_REGULAR,            
            fontSize=8,
            leading=18,                   
            textColor=colors.HexColor("#667085"),
            alignment=TA_RIGHT,  
            spaceAfter=0,
            spaceBefore=0   
        )),

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
        for idx,metric in enumerate(metrics):
            # Top: title + pill
            title_para = Paragraph(metric['title'], self.styles["box_title_style"])
            pill_para = RoundedPill(metric["pill"], colors.HexColor(metric["pill_color"]), 8, 80, 18, 8, colors.HexColor("#EFEFEF"))

            top_stack = Table(
                [[title_para, pill_para]],
                colWidths=[106,80],
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
            value_inline = Paragraph(value,self.styles["box_value_style"])
            suff_inline=Paragraph(suff,self.styles["box_decimal_style"])
            footer_para = Paragraph(metric["footer"], self.styles["box_footer_style"]) if metric.get("footer") else Spacer(1, 0)
            suff_box = Table(
                [[suff_inline]],
                style=[
                    ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 0),
                    ("TOPPADDING", (0, 0), (0, 0), 0),
                    ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ]
            )
            text_width = stringWidth(value, self.styles["box_value_style"].fontName, self.styles["box_value_style"].fontSize)
            bottom_stack = Table(
                [[value_inline, Spacer(1, 3), suff_box, footer_para]],
                colWidths=[text_width, 3, 12, None],
                style=[
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (2, 0), (2, 0), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )


            # Combine top and bottom into inner card
            inner_table = Table(
                [[top_stack], [bottom_stack]],
                colWidths=[192]
            )
            icon_path = os.path.join("staticfiles", "icons", icon_paths.get(metric['title'],""))

            icon = self.svg_icon(icon_path, width=24, height=24)

            total_table=Table([[icon,Spacer(0,8),inner_table]],colWidths=[24,8,192])
            total_table.setStyle(TableStyle([
                ("VALIGN",(0,0),(0,0),"MIDDLE"),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
                #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ]))

            padded_inner = Table([[total_table]], colWidths=[250])
            padded_inner.setStyle(TableStyle([
                ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1),6),
                #("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ]))

            rounded_card = RoundedBox(
                width=250,
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
        # story.append(PageBreak())
        # story.append(Spacer(1,22))   
        # story.extend(self.get_health_concerns_section(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_current_stack(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_family_and_history(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_health_goals(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_lifestyle_trends(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_vital_params(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_vital_params_(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_brain_function_screen(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_body_mass_index(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_body_composition(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_fitness_assesment(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_homa_ir(data))
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.extend(self.get_framingham_risk_score(data))
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

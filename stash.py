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
FONT_RALEWAY = "Raleway"

# === Register Fonts ===
pdfmetrics.registerFont(TTFont(FONT_INTER_LIGHT, "staticfiles/fonts/inter/Inter-Light.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_MEDIUM, "staticfiles/fonts/inter/Inter-Medium.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_BOLD, "staticfiles/fonts/inter/Inter-Bold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_INTER_SEMI_BOLD, "staticfiles/fonts/Inter-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_MEDIUM, "staticfiles/fonts/Raleway-Medium.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY, "staticfiles/fonts/Raleway-SemiBold.ttf"))
pdfmetrics.registerFont(TTFont(FONT_RALEWAY_REGULAR, "staticfiles/fonts/Raleway-Regular.ttf"))

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

    def __init__(self, page_width=A4[0], left_margin=72, thickness=0.001, color=colors.HexColor("#80C6C0"), spaceAfter=0):
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

        c.translate(self.left_margin-107.5, 0)

        c.setStrokeColor(self.color)
        c.setLineWidth(self.thickness)
        c.line(0, self.thickness , self.page_width, self.thickness)

        c.restoreState()

class PDFStyleConfig:
    def __init__(self):

        # --- Colors ---
        self.WHITE = colors.white
        self.PMX_GREEN = colors.HexColor("#00625B")
        self.PMX_GREEN_LIGHT = colors.HexColor("#EFE8CE")
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
            fontSize=38.426,               # ~38.426px
            textColor=colors.white,
            alignment=0,
            leading=109,
            leftIndent=0,          
            firstLineIndent=0,  
        )),

    def svg_icon(self, path, width=12, height=12):
        from reportlab.graphics.shapes import Drawing
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


    def generate(self, data: dict) -> list:
        story = []
        img_path_1 = os.path.join("staticfiles", "icons", "converted_pattern_2.png") 
        img_path_2 = os.path.join("staticfiles", "icons", "converted_pattern_3.png") 
        icon_path_pmx = os.path.join("staticfiles", "icons", "pmx_logo.svg")

        icon_pmx = self.svg_icon(icon_path_pmx, width=103, height=45.36)
        story.extend(self.add_bottom_left_image(img_path_1,x=-60,y=-755))
        story.extend(self.add_bottom_left_image(img_path_2,x=443, y=-133))
        #story.append(icon_pmx)
        main_title_1,main_title_2=data.get("main_title","Thrive limitless").split(" ")
        footer_link=data.get("footer_link","www.pmxhealth.com")
        # Create a paragraph with mixed styles
        para = Paragraph(
            # f'<font name={FONT_RALEWAY} size="100" color="#FFFFFF">{main_title_1} </font>'
            # f'<font name={FONT_RALEWAY_REGULAR} size="40" color="#D0D5DD">{main_title_2.upper()}</font>',
            f'<span fontName="{FONT_RALEWAY}" fontSize="100" textColor="#FFFFFF">{main_title_1} </span>'
            f'<span fontName="{FONT_RALEWAY_REGULAR}" fontSize="40" textColor="#D0D5DD">{main_title_2.upper()}</span>',
            self.styles["MixedInlineStyle"]
        )
        #story.append(para)
        main_sub_title_1,main_sub_title_2=data.get("main_sub_title","Longevity Roadmap").split(" ")
        para_1 = Paragraph(
            f'<font name={FONT_RALEWAY} size="38.426" color="#FFFFFF">{main_sub_title_1}</font>'
            f'<font name={FONT_RALEWAY_REGULAR} size="38.426" color="#FFFFFF"> {main_sub_title_2}</font>',
            self.styles["MixedRalewayLine"]
        )
        #story.append(para_1)
        table1=Table([
            [icon_pmx],
            [para],
            [para_1]
        ])
        table2=Table([[table1]],colWidths=[A4[0]])
        table2.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 32),
            ("RIGHTPADDING", (0, 0), (-1, -1), 32),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            #("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#FFFFFF")),

        ]))
        story.append(table2)
        #story.append(Spacer(1,20))
        # story.append(FullPageWidthHRFlowable())
        # story.append(Spacer(1,40))
        # story.append(self.get_welcome_table(data))
        # story.append(Spacer(1,40))
        # story.append(FullPageWidthHRFlowable())
        # story.append(Spacer(1, 175))       
        # story.append(PageBreak())
        # story.append(Spacer(1,22))
        # story.append(Paragraph("Table Of Contents", self.styles["TOCTitleStyle"]))
        # story.append(Spacer(1, 8))
        # story.append(self.toc_table(data))
        # story.append(Spacer(1,22))
        # story.append(self.get_user_profile_card(data))
        # story.append(Spacer(1,36))
        # story.extend(self.get_health_metrics_left_column(data))
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
                    apply_opacity(drawing, 0.3)
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

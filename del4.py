# # from reportlab.lib import colors
# # from reportlab.lib.pagesizes import letter
# # from reportlab.pdfgen import canvas

# # def hex_to_rgb(hex_color, alpha=1.0):
# #     """Convert hex to ReportLab Color with alpha."""
# #     hex_color = hex_color.lstrip('#')
# #     r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
# #     return colors.Color(r / 255, g / 255, b / 255, alpha=alpha)

# # def draw_status_bar(c, x, y, active_label, sections):
# #     """
# #     Draws a status bar with one emphasized (85x22) full-color section,
# #     and other faded (58x20) sections with 2px padding between each.
    
# #     Params:
# #     - c: ReportLab canvas
# #     - x, y: Bottom-left of the first segment
# #     - active_label: The label to highlight
# #     - sections: List of (label, hex_color)
# #     """
# #     padding = 2
# #     inactive_width = 58
# #     inactive_height = 20
# #     active_width = 85
# #     active_height = 22
# #     radius = inactive_height / 2  # rounding radius only for inactive segments

# #     # Compute total width for layout (for centering, optional)
# #     total_width = 0
# #     widths = []
# #     for label, _ in sections:
# #         w = active_width if label == active_label else inactive_width
# #         widths.append(w)
# #         total_width += w + padding
# #     total_width -= padding  # remove last extra padding

# #     current_x = x
# #     for i, (label, hex_color) in enumerate(sections):
# #         is_active = (label == active_label)
# #         width = active_width if is_active else inactive_width
# #         height = active_height if is_active else inactive_height
# #         corner_radius = height / 2 if (i == 0 or i == len(sections) - 1) else 0

# #         fill_color = hex_to_rgb(hex_color, alpha=1.0 if is_active else 0.4)
# #         c.setFillColor(fill_color)

# #         # Draw rounded rectangles if first or last
# #         if corner_radius > 0:
# #             path = c.beginPath()
# #             if i == 0:
# #                 # Left rounded
# #                 path.moveTo(current_x + corner_radius, y)
# #                 path.lineTo(current_x + width, y)
# #                 path.lineTo(current_x + width, y + height)
# #                 path.lineTo(current_x + corner_radius, y + height)
# #                 path.arcTo(current_x, y, current_x + 2*corner_radius, y + height, startAng=90, extent=180)
# #                 path.close()
# #             elif i == len(sections) - 1:
# #                 # Right rounded
# #                 path.moveTo(current_x, y)
# #                 path.lineTo(current_x + width - corner_radius, y)
# #                 path.arcTo(current_x + width - 2*corner_radius, y, current_x + width, y + height, startAng=270, extent=180)
# #                 path.lineTo(current_x, y + height)
# #                 path.close()
# #             c.drawPath(path, fill=1, stroke=0)
# #         else:
# #             c.rect(current_x, y, width, height, fill=1, stroke=0)

# #         # Text settings
# #         c.setFillColor(colors.white)
# #         c.setFont("Helvetica-Bold", 9)
# #         c.drawCentredString(current_x + width / 2, y + height / 2 - 3, label)

# #         current_x += width + padding

# # # Example usage
# # if __name__ == "__main__":
# #     c = canvas.Canvas("status_bar_active_expanded.pdf", pagesize=letter)

# #     start_x, start_y = 100, 700
# #     sections = [
# #         ("Low", "#488F31"),
# #         ("Mild", "#F49E5C"),
# #         ("Moderate", "#DE425B"),
# #         ("High","#912018")
# #     ]

# #     draw_status_bar(c, start_x, start_y, active_label="High", sections=sections)
# #     c.save()

# # from reportlab.graphics.shapes import Drawing, Circle, Path, Group
# # from reportlab.graphics import renderPDF
# # from reportlab.pdfgen import canvas
# # from reportlab.lib.colors import HexColor

# # def draw_person_icon(color="#488F31", scale=1.5):
# #     g = Group()

# #     # HEAD (circle at top)
# #     head_radius = 2 * scale
# #     head_center_x = 5 * scale
# #     head_center_y = 8.2 * scale  # keep it above the body
# #     head = Circle(head_center_x, head_center_y, head_radius, fillColor=HexColor(color), strokeColor=None)
# #     g.add(head)

# #     # BODY path (original coordinates with flip)
# #     body = Path(fillColor=HexColor(color), strokeColor=None)

# #     def pt(xp, yp):
# #         # flip Y-axis by multiplying Y with -1 and shifting upward
# #         return xp * scale, (6 - yp) * scale  # shifting to match visual orientation

# #     body.moveTo(*pt(3.72534, 6.0866))
# #     body.lineTo(*pt(1.24721, 1.37812))
# #     body.curveTo(*pt(0.658151, 0.26094),
# #                  *pt(1.84846, -0.95375),
# #                  *pt(2.97784, -0.38906))
# #     body.lineTo(*pt(4.29409, 0.26906))
# #     body.curveTo(*pt(4.65971, 0.45187),
# #                  *pt(5.09034, 0.45187),
# #                  *pt(5.45596, 0.26906))
# #     body.lineTo(*pt(6.77221, -0.38906))
# #     body.curveTo(*pt(7.90159, -0.95375),
# #                  *pt(9.08784, 0.26094),
# #                  *pt(8.50284, 1.37812))
# #     body.lineTo(*pt(6.02471, 6.0866))
# #     body.curveTo(*pt(5.53721, 7.01281),
# #                  *pt(4.21284, 7.01281),
# #                  *pt(3.72534, 6.0866))
# #     body.closePath()

# #     g.add(body)

# #     # Wrap in a Drawing
# #     drawing = Drawing(16 * scale, 20 * scale)
# #     drawing.add(g)
# #     return drawing

# # # Example usage in a PDF
# # c = canvas.Canvas("person_icon_with_circle.pdf", pagesize=(100, 100))
# # icon = draw_person_icon(scale=1.5)
# # renderPDF.draw(icon, c, 30, 10)
# # c.save()



# from reportlab.lib import colors
# from reportlab.lib.pagesizes import letter
# from reportlab.pdfgen import canvas
# from reportlab.graphics.shapes import Drawing, Circle, Path, Group
# from reportlab.graphics import renderPDF
# from reportlab.lib.colors import HexColor

# def hex_to_rgb(hex_color, alpha=1.0):
#     """Convert hex to ReportLab Color with alpha."""
#     hex_color = hex_color.lstrip('#')
#     r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
#     return colors.Color(r / 255, g / 255, b / 255, alpha=alpha)

# def draw_person_icon(color="#488F31", scale=1.5):
#     g = Group()

#     # HEAD
#     head_radius = 2 * scale
#     head_center_x = 5 * scale
#     head_center_y = 8.2 * scale
#     head = Circle(head_center_x, head_center_y, head_radius,
#                   fillColor=HexColor(color), strokeColor=None)
#     g.add(head)

#     # BODY
#     body = Path(fillColor=HexColor(color), strokeColor=None)

#     def pt(xp, yp):
#         return xp * scale, (6 - yp) * scale

#     body.moveTo(*pt(3.72534, 6.0866))
#     body.lineTo(*pt(1.24721, 1.37812))
#     body.curveTo(*pt(0.658151, 0.26094),
#                  *pt(1.84846, -0.95375),
#                  *pt(2.97784, -0.38906))
#     body.lineTo(*pt(4.29409, 0.26906))
#     body.curveTo(*pt(4.65971, 0.45187),
#                  *pt(5.09034, 0.45187),
#                  *pt(5.45596, 0.26906))
#     body.lineTo(*pt(6.77221, -0.38906))
#     body.curveTo(*pt(7.90159, -0.95375),
#                  *pt(9.08784, 0.26094),
#                  *pt(8.50284, 1.37812))
#     body.lineTo(*pt(6.02471, 6.0866))
#     body.curveTo(*pt(5.53721, 7.01281),
#                  *pt(4.21284, 7.01281),
#                  *pt(3.72534, 6.0866))
#     body.closePath()

#     g.add(body)

#     drawing = Drawing(16 * scale, 20 * scale)
#     drawing.add(g)
#     return drawing

# def draw_status_bar(c, x, y, active_label, sections):
#     padding = 2
#     inactive_width = 58
#     inactive_height = 20
#     active_width = 85
#     active_height = 22
#     radius = inactive_height / 2

#     total_width = 0
#     widths = []
#     for label, _ in sections:
#         w = active_width if label == active_label else inactive_width
#         widths.append(w)
#         total_width += w + padding
#     total_width -= padding

#     current_x = x
#     for i, (label, hex_color) in enumerate(sections):
#         is_active = (label == active_label)
#         width = active_width if is_active else inactive_width
#         height = active_height if is_active else inactive_height
#         corner_radius = height / 2 if (i == 0 or i == len(sections) - 1) else 0

#         fill_color = hex_to_rgb(hex_color, alpha=1.0 if is_active else 0.4)
#         c.setFillColor(fill_color)

#         if corner_radius > 0:
#             path = c.beginPath()
#             if i == 0:
#                 path.moveTo(current_x + corner_radius, y)
#                 path.lineTo(current_x + width, y)
#                 path.lineTo(current_x + width, y + height)
#                 path.lineTo(current_x + corner_radius, y + height)
#                 path.arcTo(current_x, y, current_x + 2*corner_radius, y + height, startAng=90, extent=180)
#                 path.close()
#             elif i == len(sections) - 1:
#                 path.moveTo(current_x, y)
#                 path.lineTo(current_x + width - corner_radius, y)
#                 path.arcTo(current_x + width - 2*corner_radius, y, current_x + width, y + height, startAng=270, extent=180)
#                 path.lineTo(current_x, y + height)
#                 path.close()
#             c.drawPath(path, fill=1, stroke=0)
#         else:
#             c.rect(current_x, y, width, height, fill=1, stroke=0)

#         c.setFillColor(colors.white)
#         c.setFont("Helvetica-Bold", 9)
#         c.drawCentredString(current_x + width / 2, y + height / 2 - 3, label)

#         # Draw person icon above active label
#         if is_active:
#             person = draw_person_icon(color=hex_color, scale=1.5)
#             icon_width = 16 * 1.5
#             icon_height = 20 * 1.5
#             icon_x = current_x + (width - icon_width) / 2
#             icon_y = y + height + 6  # some gap above the bar
#             renderPDF.draw(person, c, icon_x, icon_y)

#         current_x += width + padding

# # Run Example
# if __name__ == "__main__":
#     c = canvas.Canvas("status_bar_with_person.pdf", pagesize=letter)
#     start_x, start_y = 100, 700
#     sections = [
#         ("Low", "#488F31"),
#         ("Mild", "#F49E5C"),
#         ("Moderate", "#DE425B"),
#         ("High", "#912018")
#     ]
#     draw_status_bar(c, start_x, start_y, active_label="High", sections=sections)
#     c.save()

from reportlab.platypus import Flowable
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import io
import os
from PIL import Image as PILImage

# Constants
PAGE_WIDTH, PAGE_HEIGHT = A4
FONT_INTER_SEMI_BOLD = "Helvetica-Bold"
FONT_INTER_REGULAR = "Helvetica"
PMX_GREEN = colors.HexColor("#2DA771")


class ImageWithOverlaySVGAndText(Flowable):
    def __init__(self, image_path, svg_path, svg_x, svg_y, svg_width, svg_height, text_data):
        super().__init__()
        self.width = PAGE_WIDTH
        self.height = PAGE_HEIGHT
        self.image_path = image_path
        self.svg_path = svg_path
        self.svg_x = svg_x
        self.svg_y = svg_y
        self.svg_width = svg_width
        self.svg_height = svg_height
        self.text_data = text_data  # List of tuples: (text, x, y, style_name)

        self.styles = getSampleStyleSheet()
        self.init_styles()
        self.image_stream = self.flatten_image_to_white(image_path)

    def flatten_image_to_white(self, image_path):
        img = PILImage.open(image_path)
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = PILImage.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
        else:
            bg = img.convert("RGB")

        buffer = io.BytesIO()
        bg.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    def init_styles(self):
        self.styles.add(ParagraphStyle(
            name="overlay_text",
            fontName=FONT_INTER_SEMI_BOLD,
            fontSize=12,
            leading=14,
            textColor=PMX_GREEN,
            alignment=TA_LEFT,
        ))

    def draw(self):
        # Draw the background image
        img = ImageReader(self.image_stream)
        self.canv.drawImage(img, 0, 0, width=self.width, height=self.height)

        # Draw the SVG image
        svg_drawing = svg2rlg(self.svg_path)
        svg_drawing.width = self.svg_width
        svg_drawing.height = self.svg_height
        svg_drawing.scale(self.svg_width / svg_drawing.minWidth(), self.svg_height / svg_drawing.height)
        renderPDF.draw(svg_drawing, self.canv, self.svg_x, self.svg_y)

        # Draw text
        for text, x, y, style_name in self.text_data:
            para = Paragraph(text, self.styles[style_name])
            w, h = para.wrapOn(self.canv, self.width, self.height)
            para.drawOn(self.canv, x, y - h)


# === Example usage ===
from reportlab.platypus import SimpleDocTemplate

buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=A4)
story = []

# Paths
img_path = os.path.join("staticfiles", "icons", "genome_page.png")
svg_path = os.path.join("staticfiles", "icons", "overlay_icon.svg")

# Calculate SVG position (y from top = 162 ⇒ y from bottom = PAGE_HEIGHT - 162 - height)
svg_x = 53
svg_height = 84
svg_y = PAGE_HEIGHT - 162 - svg_height
svg_width = 181

# Add text at custom location (x=250, y=PAGE_HEIGHT - 180 for example)
text_data = [("Sample Overlay Text", 250, PAGE_HEIGHT - 180, "overlay_text")]

# Create the flowable and add to story
flowable = ImageWithOverlaySVGAndText(
    image_path=img_path,
    svg_path=svg_path,
    svg_x=svg_x,
    svg_y=svg_y,
    svg_width=svg_width,
    svg_height=svg_height,
    text_data=text_data
)
story.append(flowable)

doc.build(story)

# Save to disk if needed
with open("final_output.pdf", "wb") as f:
    f.write(buffer.getvalue())

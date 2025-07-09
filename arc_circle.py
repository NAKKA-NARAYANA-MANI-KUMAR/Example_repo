# # from reportlab.pdfgen import canvas
# # from reportlab.lib.pagesizes import A4
# # from reportlab.lib.utils import ImageReader

# # # Setup canvas
# # pdf_path = "arch_stacked_scaled_no_margins.pdf"
# # page_width, page_height = A4
# # c = canvas.Canvas(pdf_path, pagesize=A4)

# # # Load arch image
# # image_path = "arc.png"
# # image = ImageReader(image_path)

# # # Helper to convert px to pt
# # def px_to_pt(px):
# #     return px * 0.75

# # # Fixed image width (same for all)
# # image_width_px = 636.616
# # image_width_pt = px_to_pt(image_width_px)

# # # Heights for each layer (bottom to top)
# # layer_heights_px = [636.205, 530.24, 424.274, 318.308]
# # layer_heights_pt = [px_to_pt(h) for h in layer_heights_px]

# # # Scale width to fit page width exactly (no margin)
# # scale_factor = page_width / image_width_pt
# # scaled_width = page_width  # full width, no margin

# # # Start at bottom of page
# # current_y = 0

# # # Draw from largest (bottom) to smallest (top)
# # for i, height_pt in enumerate(reversed(layer_heights_pt)):
# #     scaled_height = height_pt * scale_factor
# #     x = 0  # no horizontal margin

# #     # Stop if arch goes beyond page height
# #     if current_y + scaled_height > page_height:
# #         continue

# #     c.saveState()
# #     c.setFillAlpha(0.06 + i * 0.05)
# #     c.drawImage(image, x, current_y, width=scaled_width, height=scaled_height, mask='auto')
# #     c.restoreState()

# #     # Move Y up for next layer (tight stack)
# #     current_y += 20

# # # Save
# # c.save()


# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.utils import ImageReader

# # Setup canvas
# pdf_path = "arch_cropped_to_350pt_of_itself.pdf"
# page_width, page_height = A4
# c = canvas.Canvas(pdf_path, pagesize=A4)

# # Load the arch image
# image_path = "arc.png"
# image = ImageReader(image_path)

# # Helper: px to pt conversion
# def px_to_pt(px):
#     return px * 0.75

# # Fixed image width (all same)
# image_width_px = 636.616
# image_width_pt = px_to_pt(image_width_px)

# # Heights per layer (bottom to top)
# layer_heights_px = [636.205, 530.24, 424.274, 318.308]
# layer_heights_pt = [px_to_pt(h) for h in layer_heights_px]

# # Scale image to full page width
# scale_factor = page_width / image_width_pt
# scaled_width = page_width

# # Set up clipping path: limit arch stack height to 350pt (from the base of the first arch upward)
# max_visible_arch_height = 350  # in pt
# stack_base_y = 150  # Arbitrary Y to start drawing bottom arch

# c.saveState()
# clip_path = c.beginPath()
# clip_path.rect(0, stack_base_y, page_width, max_visible_arch_height)
# c.clipPath(clip_path, stroke=0, fill=0)

# # Draw arches from largest to smallest, bottom-up
# current_y = stack_base_y

# for i, height_pt in enumerate(reversed(layer_heights_pt)):
#     scaled_height = height_pt * scale_factor
#     x = 0  # no horizontal margin

#     c.saveState()
#     c.setFillAlpha(0.06 + i * 0.05)
#     c.drawImage(image, x, current_y, width=scaled_width, height=scaled_height, mask='auto')
#     c.restoreState()

#     current_y += 20  # spacing between arches

# # Done with clipping
# c.restoreState()
# c.save()


from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# ------------------ px to pt conversion ------------------
def px_to_pt(px, dpi=96):
    """Convert pixels to points (pt)"""
    return px * 72 / dpi

# ------------------ Font Registration ------------------
# If you have Raleway-Medium.ttf in the same directory
# Otherwise, comment out the below and use Helvetica instead

pdfmetrics.registerFont(TTFont("Raleway-Medium", "staticfiles/fonts/Raleway-Medium.ttf"))
# ------------------ Style from CSS ------------------
raleway_style = ParagraphStyle(
    name="RalewayDisplayMedium",
    fontName="Raleway-Medium",                     # Or use "Helvetica" if needed
    fontSize=px_to_pt(30),                         # 30px → pt
    leading=px_to_pt(38),                          # line-height: 38px
    textColor=colors.HexColor("#00625B"),          # Brand-500 color
    alignment=TA_LEFT,
)

# ------------------ PDF Build ------------------
doc = SimpleDocTemplate("raleway_styled_output.pdf", pagesize=A4)
story = []

story.append(Paragraph("Understanding Biomarker Ranges:", raleway_style))
story.append(Spacer(1, 20))

doc.build(story)

# from reportlab.graphics.shapes import Drawing, Rect, Path
# from reportlab.lib import colors
# from reportlab.pdfgen import canvas

# def draw_pmx_range_svg_style():
#     d = Drawing(100, 180)

#     # Define bar widths and starting y position
#     bar_width = 91
#     x_start = 0

#     # Segment positions from bottom to top
#     segments = [
#         (29, "#F49E5C"),
#         (21, "#F4CE5C"),
#         (32, "#488F31"),
#         (25, "#F4CE5C"),
#         (25, "#F49E5C"),
#     ]

#     # Start from bottom at y=17 (after bottom rounded cap)
#     current_y = 17
#     for height, color in segments:
#         d.add(Rect(x_start, current_y, bar_width, height, fillColor=colors.HexColor(color), strokeColor=None))
#         current_y += height

#     # Top rounded cap
#     path_top = Path(fillColor=colors.HexColor("#DE425B"), strokeColor=None)
#     path_top.moveTo(x_start, current_y)
#     path_top.curveTo(x_start, current_y + 8, x_start + 16, current_y + 16, x_start + 16, current_y + 16)
#     path_top.lineTo(x_start + 75, current_y + 16)
#     path_top.curveTo(x_start + 91, current_y + 16, x_start + 91, current_y + 8, x_start + 91, current_y)
#     path_top.lineTo(x_start, current_y)
#     d.add(path_top)

#     # Bottom rounded cap
#     path_bottom = Path(fillColor=colors.HexColor("#DE425B"), strokeColor=None)
#     path_bottom.moveTo(x_start, 17)
#     path_bottom.lineTo(x_start, 9)
#     path_bottom.curveTo(x_start, 0, x_start + 7, 0, x_start + 16, 0)
#     path_bottom.lineTo(x_start + 75, 0)
#     path_bottom.curveTo(x_start + 91, 0, x_start + 91, 7, x_start + 91, 16)
#     path_bottom.lineTo(x_start + 91, 17)
#     path_bottom.lineTo(x_start, 17)
#     d.add(path_bottom)

#     return d

# def save_pmx_chart_pdf(filename="pmx_range_chart.pdf"):
#     c = canvas.Canvas(filename, pagesize=(200, 200))
#     d = draw_pmx_range_svg_style()
#     d.drawOn(c, 50, 20)
#     c.save()

# save_pmx_chart_pdf()


from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# Font setup
FONT_INTER_REGULAR = "Inter-Regular"
FONT_SIZE_BODY = 11

pdfmetrics.registerFont(
    TTFont(FONT_INTER_REGULAR, "staticfiles/fonts/inter/Inter-Regular.ttf")
)

# Paragraph style
custom_style = ParagraphStyle(
    name="PMXBodyText",
    fontName=FONT_INTER_REGULAR,
    fontSize=FONT_SIZE_BODY,
    textColor=colors.black,
    leading=16,
    alignment=TA_LEFT,
    spaceAfter=10,
    leftIndent=12,
)

# Data in a single line with \n preserved
instructions = "Health overview from Longevity medicine Lens\n\n1. Impaired Anabolic Drive:\nDespite strength training and adequate protein, IGF-1 is low (107 ng/mL), indicating blunted GH signaling or hepatic output. This suggests anabolic resistance at a systemic level.\n\n2. SHBG-Driven Androgen Trap:\nTotal testosterone is robust (754 ng/dL), but free testosterone is likely reduced due to suspected SHBG excess, driven by subclinical hypothyroidism (TSH 5.36) and low Vitamin D.\n\n3. Adrenal Reserve & Hormone Axis Disruption:\nDHEA-S is low-normal (111.6 µg/dL) and prolactin is elevated (18.7 ng/mL) this combination can suppress gonadal signaling, lower anabolic tone, and affect mood, drive, and recovery.\n\n4. Methylation Bottleneck:\nHomocysteine is elevated (17.82 µmol/L), suggesting suboptimal methylation, reduced nitric oxide availability, and potential endothelial stress especially important for cognitive and cardiovascular aging.\n\n5. Vitamin D Deficiency:\n25(OH)D is critically low (19.8 ng/mL), impairing immune modulation, testosterone action, and IGF-1 sensitivity. This is a key leverage point for optimizing performance and hormone function.\n\n6. Subclinical Liver & Renal Burden:\nMild elevation of SGOT (36.4 U/L) and eGFR is down to 67 mL/min, reflecting early organ load that may blunt detoxification and hormone metabolism.\n\n7. Insulin Tone & IGF-1 Crosstalk:\nLow insulin (2.84 µIU/mL) and low C-peptide (1.62) suggest reduced insulin-mediated hepatic IGF-1 generation. QUICKI is borderline low (0.42) despite normal HbA1c (4.8%).\n\n8. Subclinical Inflammation & Immune Activation:\nhs-CRP is low (0.89), but lymphocyte percentage is elevated (43.7%), hinting at low-grade chronic immune activation.\n\n9. Uric Acid on the Edge:\nUric acid is borderline high (7.2 mg/dL), which combined with methylation issues and renal load warrants dietary purine moderation and hydration support."

# PDF setup
doc = SimpleDocTemplate("formatted_health_insights.pdf", pagesize=A4,
                        rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)

# Convert \n to <br/> to preserve line breaks in PDF
# formatted_text = instructions.replace("\n\n", "<br/> •")
# formatted_text = formatted_text.replace("\n", "<br/>")

formatted_text = instructions.replace("\n", "<br/>")

# Wrap and build
paragraph = Paragraph(formatted_text, custom_style)
story = [paragraph, Spacer(1, 12)]
doc.build(story)

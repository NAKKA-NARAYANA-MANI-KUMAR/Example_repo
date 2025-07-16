from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

# --------------------- Register Font ---------------------
pdfmetrics.registerFont(TTFont('Inter-Bold', 'staticfiles/fonts/inter/Inter-Bold.ttf'))  # Update the path if needed

# --------------------- Updated Payload with 'sources' field ---------------------
heavy_metal_report = {
    "title": "Heavy Metal Test Report",
    "findings": [
        {
            "metals": ["Aluminium", "Antimony", "Arsenic", "Mercury", "Silver"],
            "level": "Moderately Elevated",
            "sources": "These can come from contaminated water, household cookware, ornaments and pesticides."
        },
        {
            "metals": ["Lead", "Bismuth", "Cadmium"],
            "level": "Moderately Elevated",
            "sources": "These are linked to neurological issues, hypertension, GI discomfort."
        },
        {
            "metals": ["Barium"],
            "level": "Moderately Elevated",
            "sources": "These can come from contaminated water or pesticides."
        }
    ]
}

# --------------------- Styles ---------------------
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name='TitleStyle',
    fontSize=16,
    leading=20,
    alignment=1,
    spaceAfter=16
))

styles.add(ParagraphStyle(
    name='BulletStyle',
    fontSize=10,
    leading=16,
    leftIndent=0,
    bulletIndent=0,
    textColor=colors.HexColor("#667085"),
    spaceAfter=6
))

# --------------------- PDF Setup ---------------------
doc = SimpleDocTemplate("heavy_metal_summary_report.pdf", pagesize=A4,
                        rightMargin=72, leftMargin=72,
                        topMargin=72, bottomMargin=18)

elements = []

# Title
elements.append(Paragraph(heavy_metal_report["title"], styles["TitleStyle"]))

# Bullet items
bullet_items = []

for finding in heavy_metal_report["findings"]:
    metals = finding["metals"]
    level = finding["level"]
    sources_text = finding.get("sources", "")

    # Styled metal names
    metal_str = ", ".join(metals)
    metal_styled = f'<font name="Inter-Bold" color="#667085">{metal_str}</font>'

    # Styled level
    level_styled = f'<font name="Inter-Bold" color="#F79009">{level}</font>'

    # Final styled paragraph
    final_text = f'{metal_styled} are {level_styled}. {sources_text}'
    bullet_items.append(ListItem(Paragraph(final_text, styles["BulletStyle"])))

# Add to document
elements.append(ListFlowable(bullet_items, bulletType='bullet', start='•'))
elements.append(Spacer(1, 12))

# Build PDF
doc.build(elements)

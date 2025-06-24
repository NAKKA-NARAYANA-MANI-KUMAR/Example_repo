from reportlab.platypus import SimpleDocTemplate, Flowable, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

PMX_GREEN = colors.HexColor("#00625B")
FADED_GREEN = colors.Color(0.0, 0.38, 0.36, alpha=0.2)  # Light outer glow

class StyledDiagnosis(Flowable):
    def __init__(self, text, width=85 * mm, height=14 * mm):
        super().__init__()
        self.text = text
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c: canvas.Canvas = self.canv
        radius = 17  # Rounded corner box

        # Rounded rectangle background
        c.setStrokeColor(colors.HexColor("#D9E9E6"))
        c.setFillColor(colors.white)
        c.roundRect(0, 0, self.width, self.height, radius, stroke=1, fill=1)

        # Bullet center position
        center_x = 6 * mm
        center_y = self.height / 2

        # 1. Outer glow circle – #D0F0EE
        c.setFillColor(colors.HexColor("#D0F0EE"))
        c.circle(center_x, center_y, 3.2 * mm, fill=1, stroke=0)

        # 2. Middle circle – #71C1BD
        c.setFillColor(colors.HexColor("#71C1BD"))
        c.circle(center_x, center_y, 2.3 * mm, fill=1, stroke=0)

        # 3. Thin white ring – #FFFFFF
        c.setFillColor(colors.white)
        c.circle(center_x, center_y, 1.65 * mm, fill=1, stroke=0)

        # 4. Innermost circle – #23968D
        c.setFillColor(colors.HexColor("#23968D"))
        c.circle(center_x, center_y, 1.6 * mm, fill=1, stroke=0)

        # Text in black
        c.setFillColor(PMX_GREEN)
        c.setFont("Helvetica", 12)
        text_x = center_x + 4.2 * mm + 3 * mm
        text_y = self.height / 2 - 3
        c.drawString(text_x, text_y, self.text)


def generate_diagnosis_pdf(filename, diagnoses):
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40)
    elements = []

    # Convert to styled flowables
    pills = [StyledDiagnosis(text) for text in diagnoses]

    # Two-column layout
    rows = []
    for i in range(0, len(pills), 2):
        row = pills[i:i+2]
        if len(row) < 2:
            row.append(Spacer(85 * mm, 14 * mm))  # Fill if odd number
        rows.append(row)

    table = Table(rows, colWidths=[90 * mm, 90 * mm], hAlign='LEFT')
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    elements.append(table)
    doc.build(elements)


# Example diagnosis list
diagnoses = [
    "ASCVD", "Folate Deficiency", "Decreased ANS Activity", "Borderline High Aortic Stiffness",
    "Vitamin B12 Insufficiency", "Vitamin D Insufficiency", "Systemic Inflammation",
    "Hypocalcemia", "Hyperprolactinemia", "Liver Parenchymal Inflammation"
]

generate_diagnosis_pdf("accurate_diagnosis_output.pdf", diagnoses)

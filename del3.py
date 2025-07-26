from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4
from pathlib import Path

def generate_areas_of_concern_pdf(output_path="areas_of_concern_output.pdf"):
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import Flowable, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

    # ---------------- Styles ----------------
    BORDER_COLOR = colors.HexColor("#EAECF0")
    OPTIMAL_COLOR = colors.HexColor("#12B76A")
    SUB_OPTIMAL_COLOR = colors.HexColor("#F79009")
    NON_OPTIMAL_COLOR = colors.HexColor("#F04438")
    TEAL_COLOR = colors.HexColor("#00625B")
    TEXT_COLOR = colors.HexColor("#667085")

    # ---------------- ConcernCard ----------------
    class ConcernCard(Flowable):
        def __init__(self, concern, width=250, height=None):
            Flowable.__init__(self)
            self.concern = concern
            self.width = width
            self.height = self._calculate_height()

        def _calculate_height(self):
            from reportlab.pdfgen import canvas
            from io import BytesIO

            tmp_canvas = canvas.Canvas(BytesIO())
            total_height = 90
            tmp_canvas.setFont("Helvetica", 12)
            name_lines = self._wrap_text(tmp_canvas, self.concern.get("name", ""), 12, self.width - 100)
            total_height += len(name_lines) * 14
            tmp_canvas.setFont("Helvetica", 9)
            desc_lines = self._wrap_text(tmp_canvas, self.concern.get("description", ""), 9, self.width - 30)
            total_height += len(desc_lines) * 12
            return total_height

        def _wrap_text(self, canvas, text, font_size, max_width):
            words = text.split()
            lines = []
            current_line = []
            current_width = 0
            for word in words:
                word_width = canvas.stringWidth(word + " ", "Helvetica", font_size)
                if current_width + word_width <= max_width:
                    current_line.append(word)
                    current_width += word_width
                else:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                    current_width = word_width
            if current_line:
                lines.append(" ".join(current_line))
            return lines

        def _get_status_color(self, status):
            status = status.lower()
            if status in ["optimal", "high", "normal"]:
                return OPTIMAL_COLOR
            if status in ["sub optimal", "medium"]:
                return SUB_OPTIMAL_COLOR
            if status in ["non optimal", "low"]:
                return NON_OPTIMAL_COLOR
            return SUB_OPTIMAL_COLOR

        def draw(self):
            c = self.canv
            c.saveState()
            c.setFillColor(colors.white)
            c.setStrokeColor(BORDER_COLOR)
            c.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=1)

            pill_width = 80
            pill_height = 22
            max_width = self.width - pill_width - 40

            c.setFont("Helvetica", 12)
            c.setFillColor(TEAL_COLOR)
            name_lines = self._wrap_text(c, self.concern.get("name", ""), 12, max_width)
            y = self.height - 25
            for line in name_lines:
                c.drawString(15, y, line)
                y -= 14

            pill_y = y + 14
            pill_x = self.width - pill_width - 15
            status = self.concern.get("status", "Sub Optimal")
            status_color = self._get_status_color(status)

            c.setFillColor(status_color)
            c.setStrokeColor(status_color)
            c.roundRect(pill_x, pill_y, pill_width, pill_height, pill_height / 2, fill=1, stroke=1)

            c.setFillColor(colors.white)
            c.setFont("Helvetica", 11)
            text_width = c.stringWidth(status, "Helvetica", 11)
            c.drawString(pill_x + (pill_width - text_width) / 2, pill_y + 6, status)

            c.setFillColor(colors.black)
            c.setFont("Helvetica", 10)
            value_text = f"{self.concern.get('value', '')} {self.concern.get('unit', '')}"
            c.drawString(15, pill_y - 25, value_text)

            range_text = self.concern.get("reference_range", "")
            text_width = c.stringWidth(range_text, "Helvetica", 10)
            c.setFillColor(colors.gray)
            c.drawString(self.width - text_width - 15, pill_y - 25, range_text)

            c.setFont("Helvetica", 9)
            c.setFillColor(TEXT_COLOR)
            desc_lines = self._wrap_text(c, self.concern.get("description", ""), 9, self.width - 30)
            y = pill_y - 50
            for line in desc_lines:
                c.drawString(15, y, line)
                y -= 12

            c.restoreState()

    # ---------------- Sample Data ----------------
    sample_data = [
        {
            "name": "Vitamin D Levels",
            "value": "18",
            "unit": "ng/mL",
            "reference_range": "30 - 100 ng/mL",
            "status": "Low",
            "description": "Low vitamin D levels can affect bone health, immunity, and mood regulation.",
        },
        {
            "name": "Cholesterol",
            "value": "220",
            "unit": "mg/dL",
            "reference_range": "< 200 mg/dL",
            "status": "High",
            "description": "High cholesterol levels increase the risk of cardiovascular disease.",
        },
        {
            "name": "HbA1c",
            "value": "6.3",
            "unit": "%",
            "reference_range": "< 5.7%",
            "status": "Sub Optimal",
            "description": "This value suggests prediabetes and indicates a need to manage blood sugar.",
        },
    ]

    # ---------------- Document Building ----------------
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = []

    # Header
    style = ParagraphStyle(name="Heading", fontSize=18, textColor=TEAL_COLOR, leading=22, spaceAfter=14)
    story.append(Paragraph("Areas of Concern", style))

    # Grid of cards: 2 columns
    card_width = (A4[0] - (2.0 * inch)) / 2
    rows = []
    temp_row = []
    for i, concern in enumerate(sample_data):
        card = ConcernCard(concern, width=card_width)
        temp_row.append(card)
        if i % 2 == 0:
            temp_row.append(Spacer(20, 1))  # gap between columns
        if len(temp_row) == 3 or i == len(sample_data) - 1:
            if len(temp_row) < 3:
                temp_row.append(Spacer(card_width, 1))  # pad row if only one card
            rows.append(temp_row)
            rows.append([Spacer(1, 15)])  # space between rows
            temp_row = []

    # Build table from rows
    if rows:
        table = Table(rows, colWidths=[card_width, 20, card_width])
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)
    else:
        story.append(Paragraph("No areas of concern found.", ParagraphStyle(name="Normal", fontSize=12)))

    # Build PDF
    doc.build(story)
    print(f"PDF successfully created: {Path(output_path).resolve()}")

# Run the function
generate_areas_of_concern_pdf()

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus.flowables import Flowable

class RoundedBox(Flowable):
    def __init__(self, width, height, content, padding=6, radius=10):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.content = content
        self.padding = padding
        self.radius = radius

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        self.canv.setStrokeColor(colors.black)
        self.canv.setLineWidth(1)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=0)

        tx = self.canv.beginText(self.padding, self.height - self.padding - 12)
        tx.setFont("Helvetica", 10)
        for line in self.content:
            tx.textLine(line)
        self.canv.drawText(tx)

# ------------------------- Document Setup -----------------------------

styles = getSampleStyleSheet()
doc = SimpleDocTemplate("split_rounded_boxes.pdf", pagesize=A4,
                        rightMargin=20, leftMargin=20,
                        topMargin=30, bottomMargin=30)

page_width, page_height = A4
usable_height = page_height - 30 - 30  # top and bottom margin

line_height = 14  # based on font size
lines_per_page = int((usable_height - 40) / line_height)  # some space for padding

# Sample lines
lines = [f"Paragraph {i+1}" for i in range(100)]

first_part = lines[:lines_per_page]
second_part = lines[lines_per_page:]

rounded1 = RoundedBox(width=page_width - 40, height=len(first_part)*line_height + 20, content=first_part)
rounded2 = RoundedBox(width=page_width - 40, height=len(second_part)*line_height + 20, content=second_part)

flowables = [rounded1, Spacer(1, 20), rounded2]

doc.build(flowables)

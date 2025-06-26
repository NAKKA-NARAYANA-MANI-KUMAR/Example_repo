from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.lib.colors import Color  

# Sample data
data = [
    ("Aluminium", "Al", 53),
    ("Antimony", "Sb", 62),
    ("Silver", "Ag", 57),
    ("Arsenic", "As", 30),
    ("Barium", "Ba", 40),
    ("Beryllium", "Be", 26),
    ("Bismuth", "Bi", 44),
    ("Cadmium", "Cd", 58),
    ("Mercury", "Hg", 70),
    ("Nickel", "Ni", 24),
    ("Platinum", "Pt", 15),
    ("Lead", "Pb", 33),
    ("Thallium", "Tl", 11),
    ("Thorium", "Th", 7),
    ("Gadolinium", "Gd", 25),
]

# Interpolate color between two
def interpolate_color(c1, c2, t):
    r = c1.red + (c2.red - c1.red) * t
    g = c1.green + (c2.green - c1.green) * t
    b = c1.blue + (c2.blue - c1.blue) * t
    return Color(r, g, b)

# Smooth color function (green → yellow → red)
def get_color(value):
    if value <= 33:
        t = value / 33.0
        return interpolate_color(colors.green, colors.yellow, t)
    else:
        t = (value - 33.0) / (100.0 - 33.0)
        return interpolate_color(colors.yellow, colors.red, t)

# PDF setup
doc = SimpleDocTemplate("heavy_metal_report.pdf", pagesize=A4)
styles = getSampleStyleSheet()
elements = []

# Title
elements.append(Paragraph("Heavy Metal Test Report", styles["Title"]))
elements.append(Spacer(1, 20))

# Drawing area
drawing_width = 550
row_height = 25
drawing_height = len(data) * row_height + 60
d = Drawing(drawing_width, drawing_height)

# Base layout positions
x_start = 120
bar_width = 300
x_end = x_start + bar_width
y_base = 30

# Simulated gradient indicator bar using tiny rectangles
segments = 100
for i in range(segments):
    pct = i / segments * 100
    col = get_color(pct)
    seg_x = x_start + (pct / 100.0) * bar_width
    seg_width = bar_width / segments
    d.add(Rect(seg_x, y_base, seg_width, 10, fillColor=col, strokeColor=None))


# Labels for zones
d.add(String(x_start, y_base - 10, "Ideal zone", fontSize=7))
d.add(String(x_start + bar_width * 0.5, y_base - 10, "to correct", fontSize=7))

# Draw each data row
for idx, (element, symbol, percent) in enumerate(data):
    y = drawing_height - (idx + 1) * row_height
    cx = x_start + (percent / 100.0) * bar_width

    # Light full-width background line
    d.add(Line(0, y - 3, x_end, y - 3, strokeColor=colors.lightgrey, strokeWidth=0.5))

    # Thick dark line from x_start to dot
    d.add(Line(x_start, y + 7, cx, y + 7, strokeColor=colors.grey, strokeWidth=1.2))

    # Left side labels
    d.add(String(0, y + 2, element, fontSize=8))
    d.add(String(95, y + 2, symbol, fontSize=8))

    # Color-coded circle
    d.add(Circle(cx, y + 7, 6, fillColor=get_color(percent), strokeColor=None))

    # Percent label
    d.add(String(cx + 8, y, f"{percent}%", fontSize=7))
    y_base = y - 3

# Vertical lines at ends
d.add(Line(x_start, y_base, x_start, drawing_height - 15, strokeColor=colors.black, strokeWidth=0.8))  # Left (thick)
d.add(Line(x_end, y_base, x_end, drawing_height - 15, strokeColor=colors.lightgrey, strokeWidth=0.4))  # Right (light)
d.add(Line(318, y_base, 318, drawing_height - 15, strokeColor=colors.lightgrey, strokeWidth=0.8))  # Left (thick)
d.add(Line(219, y_base, 219, drawing_height - 15, strokeColor=colors.lightgrey, strokeWidth=0.4))  # Right (light)

d.add(String(120, y_base -10, "0%" , fontSize=8))
d.add(String(310, y_base -10, "66%" , fontSize=8))
d.add(String(210, y_base -10, "33%" , fontSize=8))
d.add(String(410, y_base -10, "100%" , fontSize=8))

# Final build
elements.append(d)
doc.build(elements)

from reportlab.graphics.shapes import Drawing, Rect, String, Circle, Line
from reportlab.lib import colors
from reportlab.lib.colors import Color


def generate_heavy_metal_chart(data):
    def interpolate_color(c1, c2, t):
        r = c1.red + (c2.red - c1.red) * t
        g = c1.green + (c2.green - c1.green) * t
        b = c1.blue + (c2.blue - c1.blue) * t
        return Color(r, g, b)

    def get_color(value):
        abs_val = abs(value)
        if abs_val <= 33:
            t = abs_val / 33.0
            return interpolate_color(colors.HexColor("#98CA3C"), colors.HexColor("#FCB318"), t)
        else:
            t = (abs_val - 33.0) / (100.0 - 33.0)
            return interpolate_color(colors.HexColor("#FCB318"), colors.HexColor("#EF3B32"), t)

    drawing_width = 550
    row_height = 18
    drawing_height = len(data) * row_height + 60
    d = Drawing(drawing_width, drawing_height)

    # Horizontal offset for all chart elements
    x_offset = 30

    # Bar and axis settings
    bar_width = 227
    x_center = 120 + bar_width / 2 + x_offset  # midpoint is now 0%
    x_start = x_center - (bar_width / 2)
    x_end = x_center + (bar_width / 2)
    y_base = 30

    # Gradient Bar (-100 to 100)
    segments = 100
    for i in range(segments + 1):
        pct = -100 + (i / segments) * 200
        col = get_color(pct)
        seg_x = x_center + (pct / 200.0) * bar_width
        seg_width = bar_width / segments
        d.add(Rect(seg_x, y_base, seg_width, 5, fillColor=col, strokeColor=None))

    # Labels below gradient
    d.add(String(x_start, y_base - 10, "Deficient", fontSize=7))
    d.add(String(x_center - 10, y_base - 10, "Ideal", fontSize=7))
    d.add(String(x_end - 40, y_base - 10, "Excess", fontSize=7))

    # Draw data rows
    for idx, (element, symbol, value) in enumerate(data):
        y = drawing_height - (idx + 1) * row_height
        cx = x_center + (value / 200.0) * bar_width

        # Light grey baseline
        d.add(Line(0, y - 3, x_end, y - 3, strokeColor=colors.HexColor('#000000'), strokeWidth=0.01, strokeOpacity=0.1))

        # Bar line
        d.add(Line(x_center, y + 7, cx, y + 7, strokeColor=colors.HexColor("#79909B"), strokeWidth=0.503))

        # Labels
        d.add(String(0, y + 2, element, fontSize=8))
        d.add(String(95, y + 2, symbol, fontSize=8))

        # Circle and value label
        d.add(Circle(cx, y + 7, 6, fillColor=get_color(value), strokeColor=None))
        if value >= 0:
            d.add(String(cx + 8, y + 4, f"{value}%", fontSize=7))
        else:
            d.add(String(cx - 23, y + 4, f"{value}%", fontSize=7))

        y_base = y - 3

    # Vertical reference lines
    segments = [-100, -75, -50, -25, 0, 25, 50, 75, 100]
    for val in segments:
        x = x_center + (val / 200.0) * bar_width
        line_opacity = 1.0 if val == 0 else 0.1
        strokecolor = colors.HexColor("#79909B") if val == 0 else colors.HexColor("#000000")
        d.add(Line(x, y_base, x, drawing_height, strokeColor=strokecolor, strokeWidth=0.503, strokeOpacity=line_opacity))

        # Label values under gradient bar
        d.add(String(x - 10, y_base - 20, f"{val}%", fontSize=7))

    return d

from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import A4

data = [
    ("Aluminium", "Al", 53),
    ("Antimony", "Sb", 62),
    ("Silver", "Ag", -57),
    ("Arsenic", "As", 30),
    ("Barium", "Ba", 40),
    ("Beryllium", "Be", 26),
    ("Bismuth", "Bi", 44),
    ("Cadmium", "Cd", 58),
    ("Mercury", "Hg", -70),
    ("Nickel", "Ni", 24),
    ("Platinum", "Pt", 15),
    ("Lead", "Pb", 33),
    ("Thallium", "Tl", -11),
    ("Thorium", "Th", 7),
    ("Gadolinium", "Gd", -25),
]

doc = SimpleDocTemplate("your_output.pdf", pagesize=A4)
elements = []

# Get the drawing
chart = generate_heavy_metal_chart(data)
# data2=[
#     ["Vitamin A","", 66],
#     ["Vitamin C","", 86],
#     ["Vitamin E","", 76],
#     ["Vitamin B6","", 60],
#     ["Vitamin B12","", 61],
#     ["Vitamin D3","", 44],
#     ["Folic Acid(B9)","", 77]
# ]

# chart2 = generate_heavy_metal_chart(data2)

# Add to document
elements.append(chart)
# elements.append(chart2)
doc.build(elements)

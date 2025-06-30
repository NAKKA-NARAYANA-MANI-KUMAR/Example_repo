from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color
from reportlab.lib.styles import getSampleStyleSheet

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def create_gradient_drawing(width, height, colors, positions, steps=200):
    d = Drawing(width, height)
    for i in range(steps):
        ratio = i / (steps - 1)
        for j in range(len(positions) - 1):
            if positions[j] <= ratio <= positions[j + 1]:
                start_color = colors[j]
                end_color = colors[j + 1]
                local_ratio = (ratio - positions[j]) / (positions[j + 1] - positions[j])
                break
        r = start_color[0] + (end_color[0] - start_color[0]) * local_ratio
        g = start_color[1] + (end_color[1] - start_color[1]) * local_ratio
        b = start_color[2] + (end_color[2] - start_color[2]) * local_ratio
        y_pos = height * (i / steps)
        d.add(Rect(0, y_pos, width, height / steps, fillColor=Color(r, g, b), strokeWidth=0))
    return d

def draw_gradient_background(canvas, doc):
    gradient = create_gradient_drawing(width, height, rgb_colors, positions)
    renderPDF.draw(gradient, canvas, 0, 0)

# Set page size
width, height = A4

# Define gradient
hex_colors = ["#000000", "#00201E", "#152A28"]
positions = [0.0, 0.4529, 1.0]
rgb_colors = [hex_to_rgb(h) for h in hex_colors]

# Define frame
frame = Frame(0, 0, width, height, leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)

# Create document with custom onPage function
doc = BaseDocTemplate("gradient_background_fixed.pdf", pagesize=A4)
template = PageTemplate(id='FullPage', frames=[frame], onPage=draw_gradient_background)
doc.addPageTemplates([template])

# Sample content on top of gradient (optional)
styles = getSampleStyleSheet()
story = [Paragraph("This is sample text over gradient background.", styles["Title"])]

doc.build(story)

from reportlab.platypus import SimpleDocTemplate, Spacer, Flowable
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing, Path, Circle
from reportlab.graphics import renderPDF
from reportlab.lib import colors
import math

class ClockwiseArc225to315(Flowable):
    def __init__(self, strokeColor=colors.lightgrey, strokeWidth=2, radius=80):
        super().__init__()
        self.width = 200
        self.height = 100
        self.radius = radius
        self.strokeColor = strokeColor
        self.strokeWidth = strokeWidth

    def draw(self):
        center_x, center_y = 100, 100
        r = self.radius

        start_angle_deg = 225
        end_angle_deg = -45
        steps = 30

        # Create arc path
        path = Path(strokeColor=self.strokeColor, strokeWidth=self.strokeWidth)
        points = []
        for i in range(steps + 1):
            angle_deg = start_angle_deg + i * (end_angle_deg - start_angle_deg) / steps
            angle_rad = math.radians(angle_deg)
            x = center_x + r * math.cos(angle_rad)
            y = center_y + r * math.sin(angle_rad)
            points.append((x, y))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)

        d = Drawing(self.width, self.height)
        d.add(path)

        # Add circles at start and end
        start_x, start_y = points[0]
        end_x, end_y = points[-1]

        d.add(Circle(start_x, start_y, 4, fillColor=colors.green, strokeColor=colors.green))
        d.add(Circle(end_x, end_y, 4, fillColor=colors.red, strokeColor=colors.red))

        renderPDF.draw(d, self.canv, 0, 0)

# Create PDF
doc = SimpleDocTemplate("arc_with_endpoints.pdf", pagesize=A4)
elements = [
    Spacer(1, 100),
    ClockwiseArc225to315(),
    Spacer(1, 20)
]
doc.build(elements)

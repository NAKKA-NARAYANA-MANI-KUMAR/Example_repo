
from reportlab.graphics.shapes import Drawing, Path, Circle
from reportlab.graphics import renderPDF
from reportlab.platypus import Flowable, SimpleDocTemplate, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, black
from math import cos, sin, radians
from reportlab.lib.colors import Color
from reportlab.lib import colors

def lerp(p1, p2, t):
    """Linear interpolation between two points."""
    return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)

def split_bezier(p0, p1, p2, p3, t):
    """Splits a cubic Bezier curve into two at a given point t."""
    p01 = lerp(p0, p1, t)
    p12 = lerp(p1, p2, t)
    p23 = lerp(p2, p3, t)
    p012 = lerp(p01, p12, t)
    p123 = lerp(p12, p23, t)
    p0123 = lerp(p012, p123, t)
    return p01, p012, p0123

def interpolate_color(c1, c2, t):
    """Interpolates between two colors."""
    r = c1.red + (c2.red - c1.red) * t
    g = c1.green + (c2.green - c1.green) * t
    b = c1.blue + (c2.blue - c1.blue) * t
    return Color(r, g, b)

def get_color(value, col1, col2, col3):
    """Returns a color based on a value between 0 and 100, using a three-color gradient."""
    if value <= 50:
        t = value / 50.0
        return interpolate_color(HexColor(col1), HexColor(col2), t)
    else:
        t = (value - 50.0) / 50.0
        return interpolate_color(HexColor(col2), HexColor(col3), t)

def rotate_point(x, y, cx, cy, angle_degrees):
    """Rotates a point around a center point by a given angle."""
    angle = radians(angle_degrees)
    x_new = cx + (x - cx) * cos(angle) - (y - cy) * sin(angle)
    y_new = cy + (x - cx) * sin(angle) + (y - cy) * cos(angle)
    return x_new, y_new

class CustomArcFlowable(Flowable):
    def __init__(self, value: float):
        super().__init__()
        self.value = max(0, min(100, value))
        self.width = 40
        self.height = 40
        self.arc_center_x = 21.0
        self.arc_center_y = 20.0
        self._showBoundary = True
        self.segments_orig = [
            (34.7729, 37.3026),
            (38.475, 34.2, 40.9684, 29.8888, 41.8059, 25.1303),
            (42.6434, 20.3718, 41.7774, 15.4706, 39.3601, 11.2831),
            (36.9427, 7.09564, 33.1264, 3.89793, 28.5868, 2.24197),
            (24.0472, 0.586011, 19.0698, 0.586011, 14.5302, 2.24197),
            (9.99061, 3.89793, 6.17429, 7.09564, 3.75697, 11.2831),
            (1.33965, 15.4706, 0.4736, 20.3718, 1.3111, 25.1303),
            (2.14859, 29.8888, 4.64206, 34.2, 8.34417, 37.3026),
        ]
        self.rotated_segments = self._rotate_segments(self.segments_orig)
        self.start_color_hex = "#DE425B"
        self.mid_color_hex = "#F49E5C"
        self.end_color_hex = "#488F31"

    def _rotate_segments(self, segments):
        rotated = []
        for i, seg in enumerate(segments):
            if i == 0:
                x, y = rotate_point(seg[0], seg[1], self.arc_center_x, self.arc_center_y, 180)
                rotated.append((x, y))
            else:
                x1, y1 = rotate_point(seg[0], seg[1], self.arc_center_x, self.arc_center_y, 180)
                x2, y2 = rotate_point(seg[2], seg[3], self.arc_center_x, self.arc_center_y, 180)
                x3, y3 = rotate_point(seg[4], seg[5], self.arc_center_x, self.arc_center_y, 180)
                rotated.append((x1, y1, x2, y2, x3, y3))
        return rotated
    
    def draw(self):
        c = self.canv
        drawing = Drawing(self.width, self.height)
        value = self.value
        segments = self.rotated_segments
        total_segments = len(segments) - 1
        
        # Calculate a slightly reduced value to ensure the pointer stays within the arc.
        # This prevents the pointer from overlapping the end circle.
        if value > 95:
            effective_value = 95 + (value - 95) * 0.5  # Adjusts the last 5% to be shorter
        else:
            effective_value = value

        exact_segments = (effective_value / 100) * total_segments
        full_segments = int(exact_segments)
        remainder = exact_segments - full_segments

        # Background arc
        bg_path = Path(strokeColor=black, strokeWidth=0.513918, fillColor=None, strokeOpacity=0.2)
        bg_path.moveTo(*segments[0])
        for i in range(1, len(segments)):
            bg_path.curveTo(*segments[i])
        drawing.add(bg_path)

        # Start circle
        start_x, start_y = segments[0]
        cp1_x, cp1_y = segments[1][0], segments[1][1]
        dx = start_x - cp1_x
        dy = start_y - cp1_y
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length != 0:
            dx /= length
            dy /= length
        offset = 3
        start_cx = start_x + dx * offset
        start_cy = start_y + dy * offset
        start_circle = Circle(start_cx, start_cy, 2, fillColor=HexColor(self.start_color_hex), strokeColor=None)
        drawing.add(start_circle)

        # End circle
        x1, y1, x2, y2, end_x, end_y = segments[-1]
        dx = end_x - x2
        dy = end_y - y2
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length != 0:
            dx /= length
            dy /= length
        end_cx = end_x + dx * offset
        end_cy = end_y + dy * offset
        end_circle = Circle(end_cx, end_cy, 2, fillColor=HexColor(self.end_color_hex), strokeColor=None)
        drawing.add(end_circle)

        # Foreground arc
        if value > 0:
            result_color = get_color(value, self.start_color_hex, self.mid_color_hex, self.end_color_hex)
            fg_path = Path(strokeColor=result_color, strokeWidth=2.57, fillColor=None)
            
            p0 = segments[0]
            fg_path.moveTo(*p0)
            pointer_x, pointer_y = p0

            last_p = p0
            for i in range(1, full_segments + 1):
                fg_path.curveTo(*segments[i])
                last_p = (segments[i][4], segments[i][5])

            if full_segments < total_segments and remainder > 0:
                x1, y1, x2, y2, x3, y3 = segments[full_segments + 1]
                p1_split, p2_split, p3_split = split_bezier(last_p, (x1, y1), (x2, y2), (x3, y3), remainder)
                fg_path.curveTo(p1_split[0], p1_split[1], p2_split[0], p2_split[1], p3_split[0], p3_split[1])
                pointer_x, pointer_y = p3_split
            else:
                pointer_x, pointer_y = last_p
            
            drawing.add(fg_path)

            # Draw pointer circle at the end of the foreground arc
            circle = Circle(pointer_x, pointer_y, 3, fillColor=HexColor("#FFFFFF"), strokeColor=result_color, strokeWidth=1.02784)
            drawing.add(circle)
        
        if value > 0:
            # Draw value in the center
            text = f"{int(value)}"
            text_color = result_color
            font_size = 12.334
            
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", font_size)
            c.drawCentredString(self.arc_center_x, self.arc_center_y - 7, text)

        renderPDF.draw(drawing, c, x=0, y=0)

doc = SimpleDocTemplate("multi_arc_output.pdf", pagesize=letter)
story = []

for val in [0, 10, 50, 59, 75, 95, 98, 100]:
    print(f"Drawing arc for value: {val}")
    story.append(CustomArcFlowable(val))
    story.append(Spacer(0, 30))

doc.build(story)
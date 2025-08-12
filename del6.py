from reportlab.graphics.shapes import Drawing, Path, Circle, String, Rect
from reportlab.graphics import renderPDF
from reportlab.platypus import Flowable, SimpleDocTemplate, Spacer, Indenter
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black
from reportlab.lib.styles import getSampleStyleSheet
from math import cos, sin, radians
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.charts.piecharts import Pie

# --- Utility Functions ---

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

# --- Pie Chart Drawing Function ---
def create_pie_chart(data_dict):
    values = [float(v.strip('%')) for v in data_dict.values()]
    labels = list(data_dict.keys())

    colors = [
        HexColor('#DD5544'),
        HexColor('#87BD53'),
        HexColor('#55C8DD')
    ]

    # Constants
    INDICATOR_SIZE = 13.49
    SPACE_BETWEEN_INDICATORS = 3.34
    TEXT_TO_INDICATOR = 6.75
    TEXT_TO_PIE = 17.94
    FONT_SIZE = 5.396
    PIE_SIZE = 60

    # Legend total height
    legend_height = len(labels) * INDICATOR_SIZE + (len(labels) - 1) * SPACE_BETWEEN_INDICATORS

    # Drawing height = max of pie and legend heights + padding
    drawing_height = max(legend_height, PIE_SIZE) + 20
    drawing_width = 200

    drawing = Drawing(width=drawing_width, height=drawing_height)

    # Center the legend block relative to the drawing height
    legend_start_y = (drawing_height - legend_height) / 2

    for i, (label, color,value) in enumerate(zip(labels, colors,data_dict.values())):
        y = legend_start_y + (len(labels) - 1 - i) * (INDICATOR_SIZE + SPACE_BETWEEN_INDICATORS)

        # Draw square indicator
        rect = Rect(
            x=0,
            y=y,
            width=INDICATOR_SIZE,
            height=INDICATOR_SIZE,
            fillColor=color,
            strokeColor=None,
            strokeWidth=0
        )
        drawing.add(rect)

        # Draw label vertically centered with indicator
        label_x = INDICATOR_SIZE + TEXT_TO_INDICATOR
        label_y = y + (INDICATOR_SIZE - FONT_SIZE) / 2

        drawing.add(String(
            label_x,
            label_y,
            f"{label} {value}",
            fontName="Helvetica", # Using Helvetica as specified for pie chart labels
            fontSize=FONT_SIZE,
            fillColor=HexColor("#000000")
        ))

    # Add pie chart
    pie = Pie()
    pie.width = PIE_SIZE
    pie.height = PIE_SIZE
    pie.x = INDICATOR_SIZE + TEXT_TO_INDICATOR + 100 + TEXT_TO_PIE
    pie.y = (drawing_height - PIE_SIZE) / 2
    pie.data = values
    pie.labels = None

    for i, color in enumerate(colors):
        pie.slices[i].fillColor = color
        pie.slices[i].strokeColor = None
        pie.slices[i].strokeWidth = 0
        pie.slices[i].popout = 1

    drawing.add(pie)

    return drawing

# --- Custom Flowable Classes ---

class CustomArcFlowable(Flowable):
    def __init__(self, data: dict):
        super().__init__()
        self.value = max(0, min(100, data['value']))
        self.title = data['title']
        self.range_text = data['range']
        self.start_color_hex = data['start_point']
        self.end_color_hex = data['end_point']
        self.width = 216
        self.height = 54
        self.arc_center_x = 21.0
        self.arc_center_y = 20.0
        self._showBoundary = False
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
        self.mid_color_hex = "#F49E5C"

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
        
        if value > 95:
            effective_value = 95 + (value - 95) * 0.5
        else:
            effective_value = value

        exact_segments = (effective_value / 100) * total_segments
        full_segments = int(exact_segments)
        remainder = exact_segments - full_segments

        bg_path = Path(strokeColor=black, strokeWidth=0.513918, fillColor=None, strokeOpacity=0.2)
        bg_path.moveTo(*segments[0])
        for i in range(1, len(segments)):
            bg_path.curveTo(*segments[i])
        drawing.add(bg_path)

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

            circle = Circle(pointer_x, pointer_y, 3, fillColor=HexColor("#FFFFFF"), strokeColor=result_color, strokeWidth=1.02784)
            drawing.add(circle)
        
        if value > 0:
            text = f"{int(value)}"
            text_color = result_color
            font_size = 12.334
            
            c.setFillColor(text_color)
            c.setFont("Montserrat", font_size) 
            c.drawCentredString(self.arc_center_x, self.arc_center_y - 7, text)

        renderPDF.draw(drawing, c, x=0, y=0)

        title_x_pos = 41.8059 + 10.28
        font_size = 7.709
        padding = 2
        
        title_y_pos = self.arc_center_y + padding + (font_size / 2)
        range_y_pos = self.arc_center_y - padding - (font_size / 2)
        
        c.setFillColor(HexColor("#79909B"))
        c.setFont("Montserrat", font_size) 
        c.drawString(title_x_pos, title_y_pos, self.title)
        
        c.setFillColor(HexColor("#000000"))
        c.setFont("Montserrat", font_size)
        c.drawString(title_x_pos, range_y_pos, self.range_text)

class RowFlowable(Flowable):
    """
    A flowable to display two chart objects in a row, handling different chart types.
    It expects two data dictionaries, which contain 'type' to determine the chart.
    """
    def __init__(self, item1_data, item2_data):
        super().__init__()
        self.item1_data = item1_data
        self.item2_data = item2_data
        self.padding = 22
        
        # Calculate heights based on chart type to ensure consistent row height
        self.height1 = self._get_chart_height(item1_data)
        self.height2 = self._get_chart_height(item2_data)
        self.height = max(self.height1, self.height2)

        # Calculate widths based on chart type for accurate positioning
        self.width1 = self._get_chart_width(item1_data)
        self.width2 = self._get_chart_width(item2_data)
        self.width = self.width1 + self.padding + self.width2

    def _get_chart_height(self, data):
        if data.get("type") == "pie_chart":
            # Estimate height for pie chart from its constants
            chart_data = data.get("chart_data", {})
            labels = list(chart_data.keys())
            INDICATOR_SIZE = 13.49
            SPACE_BETWEEN_INDICATORS = 3.34
            PIE_SIZE = 60
            legend_height = len(labels) * INDICATOR_SIZE + (len(labels) - 1) * SPACE_BETWEEN_INDICATORS
            return max(legend_height, PIE_SIZE) + 20 # Corresponds to drawing_height in create_pie_chart
        else:
            return 54 # Fixed height for CustomArcFlowable

    def _get_chart_width(self, data):
        if data.get("type") == "pie_chart":
            return 200 # Corresponds to drawing_width in create_pie_chart
        else:
            return 216 # Fixed width for CustomArcFlowable

    def draw(self):
        # Create item1 Flowable dynamically
        if self.item1_data.get("type") == "pie_chart":
            flowable1 = create_pie_chart(self.item1_data["chart_data"])
        else: # Default to arc chart
            flowable1 = CustomArcFlowable(self.item1_data)
        
        # Create item2 Flowable dynamically
        if self.item2_data.get("type") == "pie_chart":
            flowable2 = create_pie_chart(self.item2_data["chart_data"])
        else: # Default to arc chart
            flowable2 = CustomArcFlowable(self.item2_data)

        # Calculate vertical offset for centering
        # If chart 1 is shorter, move it down by half the difference
        y_offset1 = (self.height - self.height1) / 2
        # If chart 2 is shorter, move it down by half the difference
        y_offset2 = (self.height - self.height2) / 2

        # Draw the first item with its offset
        flowable1.drawOn(self.canv, 0, y_offset1)
        # Draw the second item with its offset and horizontal spacing
        flowable2.drawOn(self.canv, self.width1 + self.padding, y_offset2)
    
class DomainHeaderFlowable(Flowable):
    """A flowable to display the header for each domain."""
    def __init__(self, header_text: str):
        super().__init__()
        self.header_text = header_text.upper() # Ensure consistent casing
        self.font_size = 13.324
        self.text_color = HexColor("#79909B")
        self.font_name = "Montserrat"
        
        self.width = 400
        self.height = self.font_size + 5

    def draw(self):
        c = self.canv
        c.setFillColor(self.text_color)
        c.setFont(self.font_name, self.font_size)
        # Apply 35 units of left padding for the header itself
        c.drawString(35, 0, self.header_text)

# --- Data and PDF Generation ---

data_structure = {
    "oxidative_stress": {
        "header": "OXIDATIVE STRESS",
        "data": [
        {
            "type": "arc_chart",
            "title": "Oxidative Aggression",
            "range": "acceptable",
            "value": 100,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        },
        {
            "type": "arc_chart",
            "title": "Antioxidant Protection",
            "range": "good",
            "value": 67,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        }
        ]
    },
    "anti_aging_skin": {
        "header": "ANTI-AGING SKIN",
        "data": [
        {
            "type": "arc_chart",
            "title": "Elasticity - Texture",
            "range": "acceptable",
            "value": 59,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Aging Condition",
            "range": "acceptable",
            "value": 48,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        },
        {
            "type": "arc_chart",
            "title": "Fragility",
            "range": "good",
            "value": 33,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        }
        ]
    },
    # Slimness now contains both an arc chart and a pie chart in its data list
    "slimness": {
        "header": "SLIMNESS",
        "data": [
            {   # This is the arc chart data for "Fat excess"
                "type": "arc_chart",
                "title": "Fat excess",
                "range": "to correct",
                "value": 52,
                "start_point": "#488F31",
                "end_point": "#DE425B"
            },
            {   # This is the pie chart data
                "type": "pie_chart",
                "chart_data": {
                    'Aqueous cellulitis tendency': '25%',
                    'Adipose cellulitis tendency': '40%',
                    'Fibrous cellulitis tendency': '35%'
                }
            }
        ]
    },
    "hair_nails": {
        "header": "HAIR / NAILS",
        "data": [
        {
            "type": "arc_chart",
            "title": "Falling tendency",
            "range": "acceptable",
            "value": 45,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        },
        {
            "type": "arc_chart",
            "title": "Quality",
            "range": "to correct",
            "value": 44,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        }
        ]
    },
    "joints": {
        "header": "JOINTS",
        "data": [
        {
            "type": "arc_chart",
            "title": "Flexibility",
            "range": "acceptable",
            "value": 64,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Acid-base balance",
            "range": "to correct",
            "value": 43,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Tissue Repair",
            "range": "acceptable",
            "value": 59,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        }
        ]
    },
    "detox": {
        "header": "DETOX",
        "data": [
        {
            "type": "arc_chart",
            "title": "Sulfoconjugation index",
            "range": "to correct",
            "value": 50,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        },
        {
            "type": "arc_chart",
            "title": "Overall Intoxication",
            "range": "bad",
            "value": 77,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        },
        {
            "type": "arc_chart",
            "title": "Metabolic overload",
            "range": "acceptable",
            "value": 42,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        }
        ]
    },
    "digestion": {
        "header": "DIGESTION",
        "data": [
        {
            "type": "arc_chart",
            "title": "Trace Mineral Assimilation",
            "range": "good",
            "value": 74,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Enzymatic balance",
            "range": "good",
            "value": 67,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Glycemic balance",
            "range": "acceptable",
            "value": 34,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        }
        ]
    },
    "mental_condition": {
        "header": "MENTAL CONDITION",
        "data": [
        {
            "type": "arc_chart",
            "title": "Cognitive function",
            "range": "acceptable",
            "value": 57,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Emotional balance",
            "range": "acceptable",
            "value": 66,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Nervous system",
            "range": "good",
            "value": 77,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        }
        ]
    },
    "general_balance": {
        "header": "GENERAL BALANCE",
        "data": [
        {
            "type": "arc_chart",
            "title": "Natural defenses",
            "range": "good",
            "value": 71,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Hormonal balance",
            "range": "good",
            "value": 72,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Cardiovascular",
            "range": "acceptable",
            "value": 56,
            "start_point": "#DE425B",
            "end_point": "#488F31"
        },
        {
            "type": "arc_chart",
            "title": "Predisposition for allergies",
            "range": "acceptable",
            "value": 95,
            "start_point": "#488F31",
            "end_point": "#DE425B"
        }
        ]
    }
}

doc = SimpleDocTemplate("multi_arc_output.pdf", pagesize=A4, leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
story = []

# Register the Montserrat font for use
try:
    pdfmetrics.registerFont(TTFont('Montserrat', 'staticfiles/fonts/Montserrat-Regular.ttf'))
except Exception as e:
    print(f"Warning: Could not register 'Montserrat' font. Using 'Helvetica'. Error: {e}")

# Process each domain
for domain_name, domain_data in data_structure.items():
    # Add domain header with 35 left padding
    story.append(DomainHeaderFlowable(domain_data["header"]))
    story.append(Spacer(1, 8)) # Space after header

    # Add 59 padding to the left for the content below the header
    story.append(Indenter(left=59))

    current_data_list = domain_data["data"]
    
    
    # Use a temporary list to accumulate items that will go into a RowFlowable
    row_flowables_data_buffer = []

    for item_data in current_data_list:
        row_flowables_data_buffer.append(item_data)
        
        # If we have two items, create a RowFlowable and append it
        if len(row_flowables_data_buffer) == 2:
            story.append(RowFlowable(row_flowables_data_buffer[0], row_flowables_data_buffer[1]))
            story.append(Spacer(1, 6)) # Vertical spacing between rows
            row_flowables_data_buffer = [] # Reset buffer

    # After the loop, if there's one item left in the buffer (odd number of items)
    if row_flowables_data_buffer:
        # Check if the single remaining item is a pie chart or arc chart
        if row_flowables_data_buffer[0].get("type") == "pie_chart":
            story.append(create_pie_chart(row_flowables_data_buffer[0]["chart_data"]))
        else:
            story.append(CustomArcFlowable(row_flowables_data_buffer[0]))
        story.append(Spacer(1, 6)) # Vertical spacing after the single item

    # Remove the 59 padding for the next domain header
    story.append(Indenter(left=-59))
    story.append(Spacer(1, 15)) # More space after each domain block for separation

doc.build(story)

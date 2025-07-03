from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib.colors import Color, white, black
from reportlab.platypus import SimpleDocTemplate, Spacer


def hex_to_color(hex_code):
    hex_code = hex_code.lstrip("#")
    return Color(int(hex_code[0:2], 16) / 255.0,
                 int(hex_code[2:4], 16) / 255.0,
                 int(hex_code[4:6], 16) / 255.0)


def interpolate_color(c1, c2, t):
    r = c1.red + (c2.red - c1.red) * t
    g = c1.green + (c2.green - c1.green) * t
    b = c1.blue + (c2.blue - c1.blue) * t
    return Color(r, g, b)


def lighten_color(color, factor=0.4):
    return Color(
        color.red + (1.0 - color.red) * factor,
        color.green + (1.0 - color.green) * factor,
        color.blue + (1.0 - color.blue) * factor
    )


def get_multicolor_gradient(t, color_stops):
    for i in range(len(color_stops) - 1):
        if color_stops[i][0] <= t <= color_stops[i + 1][0]:
            t_local = (t - color_stops[i][0]) / (color_stops[i + 1][0] - color_stops[i][0])
            return interpolate_color(color_stops[i][1], color_stops[i + 1][1], t_local)
    return color_stops[-1][1]


def draw_gradient_score_bar(width=478, height=6, score=102, data_min=80, data_max=120, label_text="Very Low"):
    gradient_colors = [
        (0.0, hex_to_color("#ED005F")),
        (0.351, hex_to_color("#F49E5C")),
        (0.7019, hex_to_color("#F4CE5C")),
        (1.0, hex_to_color("#488F31")),
    ]

    radius = 16
    y = 20
    label_y = 6
    d = Drawing(width, height + 80)

    # Background bar
    d.add(Rect(0, y, width, height, rx=radius, ry=radius, fillColor=white, strokeColor=None))

    # Gradient fill
    segments = 600
    for i in range(segments):
        t = i / (segments - 1)
        color = get_multicolor_gradient(t, gradient_colors)
        x = t * width
        seg_width = width / segments
        d.add(Rect(x, y, seg_width + 1, height, fillColor=color, strokeColor=None))

    # Labels under bar
    d.add(String(0, label_y, "Low", fontSize=7, fillColor=black))
    d.add(String(width / 2 - 15, label_y, "Average", fontSize=7, fillColor=black))
    d.add(String(width - 30, label_y, "High", fontSize=7, fillColor=black))

    # Score mapping
    clamped_score = max(data_min, min(score, data_max))
    score_ratio = (clamped_score - data_min) / (data_max - data_min)
    score_x = score_ratio * width

    # Score pill
    score_pill_width = 38
    score_pill_height = 20
    score_pill_y = y + height / 2 - score_pill_height / 2
    score_pill_color = get_multicolor_gradient(score_ratio, gradient_colors)
    score_fill = lighten_color(score_pill_color, factor=0.5)

    d.add(Rect(score_x - score_pill_width / 2, score_pill_y, score_pill_width, score_pill_height,
               rx=score_pill_height / 2, ry=score_pill_height / 2,
               fillColor=score_fill, strokeColor=score_pill_color, strokeWidth=1))

    score_text = str(score)
    score_text_x = score_x - (len(score_text) * 5 / 2)
    d.add(String(score_text_x, score_pill_y + 6, score_text, fontSize=10.435, fillColor=black))

    # Floating pill (top right corner)
    float_pill_width = 80
    float_pill_height = 18
    float_pill_x = width - float_pill_width
    float_pill_y = y + height + 22
    float_fill = score_pill_color

    d.add(Rect(float_pill_x, float_pill_y, float_pill_width, float_pill_height,
               rx=float_pill_height / 2, ry=float_pill_height / 2,
               fillColor=float_fill, strokeColor=None))

    # Centered label text in pill
    float_text_size = 8
    float_text_width = len(label_text) * 4.5
    float_text_x = float_pill_x + (float_pill_width - float_text_width) / 2

    d.add(String(float_text_x, float_pill_y + 5, label_text, fontSize=float_text_size, fillColor=white))

    return d


# Build PDF
doc = SimpleDocTemplate("cognitive_attention_bar.pdf")
elements = [draw_gradient_score_bar(score=106, data_min=80, data_max=120, label_text="Low"), Spacer(1, 20)]
doc.build(elements)
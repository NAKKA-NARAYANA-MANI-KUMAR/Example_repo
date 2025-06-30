# from reportlab.platypus import SimpleDocTemplate, Image
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.units import inch

# # Create a PDF document
# doc = SimpleDocTemplate("top_left_image_platypus.pdf", pagesize=A4,
#                         topMargin=-10, leftMargin=-10, rightMargin=0, bottomMargin=0)

# # Path to your image
# image_path = "converted_pattern_2.png"  # Replace with your image file path

# # Define image size
# img_width = 50  # in points (~1.4 inches)
# img_height = 50

# # Create Image Flowable
# img = Image(image_path, width=img_width, height=img_height)
# img.hAlign = 'LEFT'  # <--- THIS forces alignment to top-left

# # Add the image to the flowable list
# elements = [img]

# # Build the PDF
# doc.build(elements)



from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Flowable, Image
from reportlab.lib.pagesizes import A4,letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
from reportlab.lib.units import mm
import json

page_width, page_height = A4

print("Page width (in points):", page_width)
print("Page height (in points):", page_height)


# JSON Data
data_json = '''
{
  "id": "PMX010000",
  "name": "Rohan Nanda",
  "gender": "Male",
  "city": "Hyderabad",
  "pincode": "500065",
  "occupation": "Business",
  "dob": "27/03/1985",
  "doa": "06/06/2025",
  "diet": "Omnivore"
}
'''
data = json.loads(data_json)

# Icon paths
icon_paths = {
    "avatar": "staticfiles/icons/Dp.png",
    "id": "staticfiles/icons/pmx_x.svg",
    "gender": "staticfiles/icons/gender_male.svg",
    "location": "staticfiles/icons/location.svg",
    "briefcase": "staticfiles/icons/business.svg",
    "dob_calendar": "staticfiles/icons/dob_calendar.svg",
    "doa_calendar": "staticfiles/icons/calendar.svg",
    "diet": "staticfiles/icons/food.svg"
}

# Styles
info_style = ParagraphStyle('Info', fontSize=10, leading=13, textColor=colors.HexColor("#333333"))
name_style = ParagraphStyle('Name', fontSize=14, leading=16, spaceAfter=4, fontName="Helvetica-Bold")

# SVG to Flowable
class SVGImage(Flowable):
    def __init__(self, svg_path, width=6*mm, height=6*mm):
        super().__init__()
        try:
            drawing = svg2rlg(svg_path)
            if not drawing:
                raise ValueError(f"Could not load SVG: {svg_path}")
        except Exception as e:
            print(f"Failed to load SVG at {svg_path} — {e}")
            self.drawing = None
            self.width = 0
            self.height = 0
            return
        self.drawing = drawing
        self.width = width
        self.height = height
        scale_x = self.width / drawing.width
        scale_y = self.height / drawing.height
        self.drawing.width *= scale_x
        self.drawing.height *= scale_y
        for elem in self.drawing.contents:
            elem.scale(scale_x, scale_y)

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        if self.drawing:
            renderPDF.draw(self.drawing, self.canv, 0, 0)

# ... (all previous imports and definitions remain the same) ...

# Function: icon + text in a horizontal mini table
def icon_text(icon_key, text, width=52*mm):
    icon = SVGImage(icon_paths[icon_key], width=5.5*mm, height=5.5*mm)
    paragraph = Paragraph(text, info_style)
    mini_table = Table([[icon, paragraph]],
                       colWidths=[6*mm, width - 6*mm])
    mini_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)
    ]))
    return mini_table

# Top info row (ID and name), padded to 3 columns
id_row = Table([[
    '',
    icon_text("id", f"ID - {data['id']}"),
      # empty cell to keep structure
    Paragraph(f"<b>{data['name']}</b>", name_style)
]], colWidths=[53*mm, 5*mm, 102*mm])  # padding second column slightly

# Row with gender, location, occupation
row3 = Table([[
    icon_text("gender", data["gender"]),
    icon_text("location", f"{data['city']} - {data['pincode']}"),
    icon_text("briefcase", data["occupation"])
]], colWidths=[53*mm, 53*mm, 53*mm])

# Row with DOB, DOA, empty
row4 = Table([[
    icon_text("dob_calendar", f"D.O.B - {data['dob']}"),
    icon_text("doa_calendar", f"D.O.A - {data['doa']}"),
]], colWidths=[53*mm, 53*mm, 53*mm])

# Row with Diet and two empty cells
row5 = Table([[
    '',
    icon_text("diet", f"Dietary Preference - {data['diet']}"),
    ''
]], colWidths=[53*mm, 53*mm, 53*mm])

# Assemble right-side content
right_content = Table(
    [[id_row], [row3], [row4], [row5]],
    colWidths=[160*mm]
)
right_content.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 2),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 2)
]))

# Avatar on the left
avatar_img = Image(icon_paths["avatar"], width=30*mm, height=30*mm)

# Combine avatar + content
main_table = Table(
    [[avatar_img, Spacer(6 * mm, 0), right_content]],
    colWidths=[32*mm, 5*mm, 125*mm]
)
main_table.setStyle(TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP")
]))

# Build PDF
doc = SimpleDocTemplate("final_card_layout.pdf", pagesize=A4,
                        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
doc.build([main_table])

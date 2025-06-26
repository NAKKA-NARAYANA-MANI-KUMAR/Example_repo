from reportlab.platypus import SimpleDocTemplate, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

# Create a PDF document
doc = SimpleDocTemplate("top_left_image_platypus.pdf", pagesize=A4,
                        topMargin=-10, leftMargin=-10, rightMargin=0, bottomMargin=0)

# Path to your image
image_path = "converted_pattern_2.png"  # Replace with your image file path

# Define image size
img_width = 50  # in points (~1.4 inches)
img_height = 50

# Create Image Flowable
img = Image(image_path, width=img_width, height=img_height)
img.hAlign = 'LEFT'  # <--- THIS forces alignment to top-left

# Add the image to the flowable list
elements = [img]

# Build the PDF
doc.build(elements)

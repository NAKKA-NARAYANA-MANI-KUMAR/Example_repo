from reportlab.pdfgen import canvas
Textlines = [
    "If you've corrected the code and you're still",
    "getting a corrupted PDF, then here are the",
    "next possible causes and solutions."
]
file_name = 'mydoc.pdf'
pdf = canvas.Canvas(file_name)
pdf.setTitle('manis document')

# for font in pdf.getAvailableFonts():
#     print(font)

from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

#1.To set the title
pdf.drawCentredString(270,770, 'mani')  # Use proper coordinates (X=100, Y=750)


#2.to set the sub title

pdf.setFillColorRGB(0,255,0)
pdf.setFont("Courier-Bold",20)
pdf.drawCentredString(290,720,'This is my document')

#3.Draw the line

pdf.line(30,710,550,710)

#4Text Object :: for large amounts of text
from reportlab.lib import colors

text=pdf.beginText(40,680)
text.setFont("Courier",16)
text.setFillColor(colors.red)
for line in Textlines:
    text.textLine(line)

pdf.drawText(text)

#4.image insertion

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

image_path = 'google.png'
img = ImageReader(image_path)
img_width, img_height = img.getSize()
print(f'img_width:{img_width},img_height:{img_height}')
# Desired max width and height on page
max_width = 300
max_height = 300

# Scale the image while maintaining aspect ratio
scale = min(max_width / img_width, max_height / img_height)
scaled_width = img_width * scale
scaled_height = img_height * scale

# Set position (x, y)
x = 100
y = 300  # adjust so image is clearly visible on the page

# Draw the scaled image
pdf.drawInlineImage(image_path, x, y, width=scaled_width, height=scaled_height)


#pdf.drawInlineImage('google.png',10,10)
pdf.save()
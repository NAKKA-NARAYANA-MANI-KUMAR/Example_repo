from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

styles = getSampleStyleSheet()
styleN = styles["Normal"]

raw_data = [
    ["Full Name", "Age (Years)", "City of Residence", "Current Occupation"],
    ["Alice Johnson, B.Tech in Computer Science", "30 years old", "Downtown area, New York City, NY","Senior Software Engineer working at TechNova Inc., specialized in backend systems"],
    ["Bob Martinez, BA in Graphic Design", "25 years of age", "Suburban district, Los Angeles, California","Creative UI/UX Designer currently employed at Creative Studio Lab"],
    ["Charlie O'Donnell, MBA Graduate", "35 years old", "Northern side, Chicago, Illinois","Experienced Project Manager at Urban Infrastructure Group handling commercial projects"],
    ["Diana Thompson, MSc in Marketing", "28 years old", "Central area, Austin, Texas","Market Research Analyst working at BrightWave Solutions in digital strategy division"],
    ["Edward Kim, PhD in Data Science", "32 years old", "Bay Area, San Francisco, CA","Lead Data Scientist at Quantum Analytics Corp, focusing on predictive modeling"],
    ["Fatima Sheikh, PMP Certified", "29 years old", "North Seattle, Washington","Product Manager overseeing SaaS development at CloudWorks Technologies"],
    ["Alice Johnson, B.Tech in Computer Science", "30 years old", "Downtown area, New York City, NY","Senior Software Engineer working at TechNova Inc., specialized in backend systems"],
    ["Bob Martinez, BA in Graphic Design", "25 years of age", "Suburban district, Los Angeles, California","Creative UI/UX Designer currently employed at Creative Studio Lab"],
    ["Charlie O'Donnell, MBA Graduate", "35 years old", "Northern side, Chicago, Illinois","Experienced Project Manager at Urban Infrastructure Group handling commercial projects"],
    ["Diana Thompson, MSc in Marketing", "28 years old", "Central area, Austin, Texas","Market Research Analyst working at BrightWave Solutions in digital strategy division"],
    ["Edward Kim, PhD in Data Science", "32 years old", "Bay Area, San Francisco, CA","Lead Data Scientist at Quantum Analytics Corp, focusing on predictive modeling"],
    ["Fatima Sheikh, PMP Certified", "29 years old", "North Seattle, Washington","Product Manager overseeing SaaS development at CloudWorks Technologies"],
    ["Alice Johnson, B.Tech in Computer Science", "30 years old", "Downtown area, New York City, NY","Senior Software Engineer working at TechNova Inc., specialized in backend systems"],
    ["Bob Martinez, BA in Graphic Design", "25 years of age", "Suburban district, Los Angeles, California","Creative UI/UX Designer currently employed at Creative Studio Lab"],
    ["Charlie O'Donnell, MBA Graduate", "35 years old", "Northern side, Chicago, Illinois","Experienced Project Manager at Urban Infrastructure Group handling commercial projects"],
    ["Diana Thompson, MSc in Marketing", "28 years old", "Central area, Austin, Texas","Market Research Analyst working at BrightWave Solutions in digital strategy division"],
    ["Edward Kim, PhD in Data Science", "32 years old", "Bay Area, San Francisco, CA","Lead Data Scientist at Quantum Analytics Corp, focusing on predictive modeling"],
    ["Fatima Sheikh, PMP Certified", "29 years old", "North Seattle, Washington","Product Manager overseeing SaaS development at CloudWorks Technologies"],
    ["Alice Johnson, B.Tech in Computer Science", "30 years old", "Downtown area, New York City, NY","Senior Software Engineer working at TechNova Inc., specialized in backend systems"],
    ["Bob Martinez, BA in Graphic Design", "25 years of age", "Suburban district, Los Angeles, California","Creative UI/UX Designer currently employed at Creative Studio Lab"],
    ["Charlie O'Donnell, MBA Graduate", "35 years old", "Northern side, Chicago, Illinois","Experienced Project Manager at Urban Infrastructure Group handling commercial projects"],
    ["Diana Thompson, MSc in Marketing", "28 years old", "Central area, Austin, Texas","Market Research Analyst working at BrightWave Solutions in digital strategy division"],
    ["Edward Kim, PhD in Data Science", "32 years old", "Bay Area, San Francisco, CA","Lead Data Scientist at Quantum Analytics Corp, focusing on predictive modeling"],
    ["Fatima Sheikh, PMP Certified", "29 years old", "North Seattle, Washington","Product Manager overseeing SaaS development at CloudWorks Technologies"]

]

# Convert all values to Paragraphs so that word wrapping works
data = [[Paragraph(cell, styleN) for cell in row] for row in raw_data]

pdf = SimpleDocTemplate("wrapped_table.pdf", pagesize=A4)

# Create the table
table = Table(data, repeatRows=1, colWidths=[140, 80, 140, 180])  # Adjusted widths

# Table styling
style = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.green),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
])

# Alternate row colors
for i in range(1, len(data)):
    bg_color = colors.beige if i % 2 == 0 else colors.burlywood
    style.add('BACKGROUND', (0, i), (-1, i), bg_color)

table.setStyle(style)

# Build PDF
pdf.build([table])

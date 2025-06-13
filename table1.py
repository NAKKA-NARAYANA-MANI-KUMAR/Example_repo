data = [
    ["Full Name", "Age (Years)", "City of Residence", "Current Occupation"],
    ["Alice Johnson, B.Tech in Computer Science", "30 years old", "Downtown area, New York City, NY", "Senior Software Engineer working at TechNova Inc., specialized in backend systems"],
    ["Bob Martinez, BA in Graphic Design", "25 years of age", "Suburban district, Los Angeles, California", "Creative UI/UX Designer currently employed at Creative Studio Lab"],
    ["Charlie O'Donnell, MBA Graduate", "35 years old", "Northern side, Chicago, Illinois", "Experienced Project Manager at Urban Infrastructure Group handling commercial projects"],
    ["Diana Thompson, MSc in Marketing", "28 years old", "Central area, Austin, Texas", "Market Research Analyst working at BrightWave Solutions in digital strategy division"]
]


file_name="table1.pdf"

from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.pagesizes import letter

pdf=SimpleDocTemplate(
    file_name,
    pagesize=letter
)

from reportlab.platypus import Table
table =Table(data)

from reportlab.platypus import TableStyle
from reportlab.lib import colors

style=TableStyle([
    ('BACKGROUND',(0,0),(3,0),colors.green),
    ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
    ('ALIGN',(0,0),(-1,-1),'CENTER'),
    #('FONTNAME',(0,0),(-1,0),'Courier-Bold'),
    ('FONTSIZE',(0,0),(-1,0),14),
    ('BOTTOMPADDING',(0,0),(-1,0),12),
    ('BACKGROUND',(0,1),(-1,-1),colors.beige)
])
table.setStyle(style)

#2.Alternate background color
rownumb=len(data)
for i in range(1,rownumb):
    if i%2==0:
        bc=colors.burlywood
    else:
        bc=colors.beige
    ts=TableStyle([
        ('BACKGROUND',(0,i),(-1,i),bc)
    ])
    table.setStyle(ts)

#Add Boarders
ts=TableStyle([
    ('BOX',(0,0),(-1,-1),1,colors.black),
    ('LINEBEFORE',(2,1),(2,-1),1,colors.blue),
    ('LINEABOVE',(0,2),(-1,3),1,colors.red),
    ('GRID',(0,1),(-1,-1),1,colors.black)
])
table.setStyle(ts)
elems=[]
elems.append(table)
pdf.build (elems)

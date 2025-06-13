data = [
    ["Name", "Age", "City", "Occupation"],
    ["Alice", "30", "New York", "Engineer"],
    ["Bob", "25", "Los Angeles", "Designer"],
    ["Charlie", "35", "Chicago", "Manager"]
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
elems=[]
elems.append(table)
pdf.build (elems)

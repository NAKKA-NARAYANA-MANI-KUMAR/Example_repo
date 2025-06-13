from flask import Flask, request, send_file, make_response
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO

app = Flask(__name__)

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        # Extract JSON input
        raw_data = request.get_json()

        if not isinstance(raw_data, list) or not all(isinstance(row, list) for row in raw_data):
            return {"error": "Input must be a list of lists (rows of table)"}, 400

        # Style setup
        styles = getSampleStyleSheet()
        styleN = styles["Normal"]

        # Wrap all cells in Paragraph to enable text wrapping
        data = [[Paragraph(str(cell), styleN) for cell in row] for row in raw_data]

        # Create a BytesIO buffer instead of writing to disk
        buffer = BytesIO()
        pdf = SimpleDocTemplate(buffer, pagesize=A4)

        # Define column widths
        colWidths = [140, 80, 140, 180]

        # Create the table with repeat header
        table = Table(data, repeatRows=1, colWidths=colWidths)

        # Table styling
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.green),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ])

        # Add alternating row colors (excluding header)
        for i in range(1, len(data)):
            bg_color = colors.beige if i % 2 == 0 else colors.burlywood
            style.add('BACKGROUND', (0, i), (-1, i), bg_color)

        table.setStyle(style)

        # Build PDF
        pdf.build([table])

        # Rewind buffer to beginning
        buffer.seek(0)

        # Send as HTTP response
        return send_file(
            buffer,
            as_attachment=True,
            download_name="generated_table.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(debug=True)

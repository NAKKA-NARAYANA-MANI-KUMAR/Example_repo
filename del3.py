import os
from typing import Tuple
from io import BytesIO

import fitz  # PyMuPDF
from PIL import Image, ImageDraw
from reportlab.platypus import SimpleDocTemplate, Spacer, Image as RLImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch

class ThriveRoadmapTemplate:
    @staticmethod
    def crop_pdf_styled(pdf_path: str, page_number: int, crop_rect: Tuple[float, float, float, float], max_width: int = 500, max_height: int = 600) -> RLImage:
        """
        Crop a region from a PDF page, apply styles, and return a ReportLab Image.
        """
        # Check if file exists
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        # Load PDF and crop region
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        rect = fitz.Rect(*crop_rect)
        cropped_pix = page.get_pixmap(clip=rect, dpi=200)
        doc.close()

        # Convert pixmap to PIL Image
        cropped_image = Image.frombytes("RGB", (cropped_pix.width, cropped_pix.height), bytes(cropped_pix.samples))

        # Create gradient background
        gradient = Image.new("RGB", cropped_image.size, "#02665F")
        for y in range(gradient.height):
            gradient.paste((2, 102, 95), (0, y, gradient.width, y + 1))

        # Blend cropped image with gradient
        blended = Image.blend(gradient, cropped_image, alpha=0.7)

        # Add rounded corners
        mask = Image.new("L", blended.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, blended.width, blended.height], radius=20, fill=255)

        # Apply mask for rounded corners
        blended = blended.convert("RGBA")
        blended.putalpha(mask)

        # Resize image to fit PDF size constraints
        width, height = blended.size
        scale = min(max_width / width, max_height / height, 1.0)
        new_size = (int(width * scale), int(height * scale))
        print(f"Original size: {width}x{height}, Scaled size: {new_size}")
        blended = blended.resize(new_size, Image.LANCZOS)

        # Save image to BytesIO as PNG
        image_bytes = BytesIO()
        blended.save(image_bytes, format="PNG")
        image_bytes.seek(0)

        # Create ReportLab Image object with correct dimensions
        rl_image = RLImage(image_bytes, width=new_size[0], height=new_size[1])
        rl_image._restrictSize(max_width, max_height)
        return rl_image


if __name__ == "__main__":
    # Input and output paths
    pdf_path = r"C:\Users\Admin\Downloads\DEXASCAN-NAINA-SAXENA_Y7rTnwm.pdf"
    output_pdf_path = r"C:\Users\Admin\Downloads\output.pdf"

    # Create the output PDF using ReportLab
    doc = SimpleDocTemplate(output_pdf_path, pagesize=A4)
    story = []

    # Crop and style a portion of the PDF and add it to the PDF
    cropped_image = ThriveRoadmapTemplate.crop_pdf_styled(
        pdf_path=pdf_path,
        page_number=0,
        crop_rect=(8, 280, 200, 570),  # (x0, y0, x1, y1)
        max_width=400,
        max_height=500
    )
    story.append(cropped_image)
    story.append(Spacer(1, 0.2 * inch))

    # Build the final PDF
    doc.build(story)
    print(f"✅ PDF created at: {output_pdf_path}")

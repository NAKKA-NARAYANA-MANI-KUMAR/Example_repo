import json
import logging
import os
import shutil
from datetime import datetime
from typing import Any

from PIL import Image, ImageDraw
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
from svglib.svglib import svg2rlg

from ..internal_report_generator import InternalReportGenerator
from ..pdf.pages.base.pmx_base_page import PMXBasePage
from ..pdf.pages.prescription_page import PrescriptionPage
from ..utils import get_report_asset_path
from .base_generator import BaseReportGenerator
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self._saved_pages = []
        super().__init__(*args, **kwargs)

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_pages)
        for page_num, page in enumerate(self._saved_pages, start=1):
            self.__dict__.update(page)
            self._template.total_pages = total_pages  # set total pages for footer
            self._template._add_logo_to_bottom_left(self, self._doc)
            super().showPage()
        super().save()


class PrescriptionReportGenerator(BaseReportGenerator):
    """Generator for prescription reports"""

    def __init__(self, storage_service=None):
        super().__init__(storage_service)
        self.report_generator = InternalReportGenerator(report_type="prescription")
        self.show_guides = False  # Add default value for show_guides

    def populate_data(self, report: Any) -> dict[str, Any]:
        """Populate prescription report data

        Args:
            report: InternalReport instance

        Returns:
            Dict containing populated report data
        """
        logger.info("=== Starting Prescription Data Population ===")
        source_data = report.source_data or {}
        precheck_data = source_data.get("precheck", [])
        consultation_data = source_data.get("consultation", {})

        logger.info(f"Source Data: {json.dumps(source_data, indent=2, default=str)}")
        logger.info(
            f"PreCheck Data: {json.dumps(precheck_data, indent=2, default=str)}"
        )
        logger.info(
            f"Consultation Data: {json.dumps(consultation_data, indent=2, default=str)}"
        )

        # Initialize prescription data structure
        prescription_data = {
            "report_info": {
                "type": report.report_type,
                "generated_date": datetime.now().strftime("%Y-%m-%d"),
                "clinic": {
                    "name": "PMX Health",
                    "address": "4th floor, Rd Number 44, Jubilee Hills, Hyderabad, Telangana - 500033",
                },
            },
            "source_data": source_data,
            "client": {
                "id": "",
                "name": "",
                "gender": "",
                "location": "",
                "dob": "",
                "blood_group": "",
            },
            "vitals": [],
            "medications": source_data.get(
                "medications", []
            ),  # Default, may override below
            "therapies": source_data.get("therapies", []),
            "symptoms": [
                symptom["name"] for symptom in consultation_data.get("symptoms", [])
            ],
            "signs": [],
            "labs": [
                t.get("name", "") if isinstance(t, dict) else getattr(t, "name", "")
                for t in consultation_data.get("labs", [])
            ],
            "diagnoses": [],
            "lab_recommendations": [],
            "advices": [],
            "follow_up": {"next_visit_on": "", "notes": ""},
        }

        # If consultation reference_data has medications, use those (ensures available_in_clinic/external_url are included)
        if (
            "reference_data" in consultation_data
            and "medications" in consultation_data["reference_data"]
        ):
            prescription_data["medications"] = consultation_data["reference_data"][
                "medications"
            ]

        # Ensure external_url is always present for PDF logic
        for med in prescription_data["medications"]:
            if "external_url" not in med:
                med["external_url"] = ""

        # Fill profile data
        if report.user:
            prescription_data["client"].update(
                {
                    "name": getattr(report.user, "first_name", "") or "",
                    "gender": getattr(report.user, "gender", ""),
                    "location": getattr(report.user, "location", ""),
                    "age": getattr(report.user, "age", ""),
                    "phone": getattr(report.user, "phone", ""),
                    "email": getattr(report.user, "email", ""),
                }
            )

            # Expand gender abbreviations
            if prescription_data["client"]["gender"] == "M":
                prescription_data["client"]["gender"] = "Male"
            elif prescription_data["client"]["gender"] == "F":
                prescription_data["client"]["gender"] = "Female"

            # Set date of birth if exists
            if hasattr(report.user, "date_of_birth") and report.user.date_of_birth:
                prescription_data["client"]["dob"] = report.user.date_of_birth.strftime(
                    "%Y-%m-%d"
                )

                # If age is not set but we have DOB, calculate age
                if not prescription_data["client"]["age"] and report.user.date_of_birth:
                    try:
                        today = datetime.now().date()
                        dob = report.user.date_of_birth
                        if isinstance(dob, datetime):
                            dob = dob.date()
                        age = (
                            today.year
                            - dob.year
                            - ((today.month, today.day) < (dob.month, dob.day))
                        )
                        prescription_data["client"]["age"] = age
                        logger.info(
                            f"Calculated age from DOB in prescription generator: {age}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Error calculating age from DOB in prescription generator: {e}"
                        )

            # Log client data for debugging
            logger.info(
                f"Client data after population: {json.dumps(prescription_data['client'], default=str)}"
            )

        # Fill consultation data
        if consultation_data:
            prescription_data.update(
                {
                    "signs": [
                        s.get("name", "")
                        if isinstance(s, dict)
                        else getattr(s, "name", "")
                        for s in consultation_data.get("signs", [])
                    ],
                    "tests": [
                        t.get("name", "")
                        if isinstance(t, dict)
                        else getattr(t, "name", "")
                        for t in consultation_data.get("labs", [])
                    ],
                    "diagnoses": [
                        d.get("name", "")
                        if isinstance(d, dict)
                        else getattr(d, "name", "")
                        for d in consultation_data.get("diagnoses", [])
                    ],
                    "lab_recommendations": [
                        lab.get("name", "")
                        if isinstance(lab, dict)
                        else getattr(lab, "name", "")
                        if hasattr(lab, "name")
                        else getattr(lab, "lab_id", "")
                        for lab in consultation_data.get("lab_recommendations", [])
                        or consultation_data.get("labs", [])
                        or []
                    ],
                    "advices": [
                        adv.get("name", "")
                        if isinstance(adv, dict)
                        else getattr(adv, "name", "")
                        for adv in consultation_data.get("advices", [])
                    ],
                }
            )

            # Fill follow up
            follow_up_date = consultation_data.get("follow_up_date", "")
            follow_up_notes = consultation_data.get("follow_up_notes", "")
            if follow_up_date or follow_up_notes:
                prescription_data["follow_up"].update(
                    {
                        "next_visit_on": follow_up_date.split("T")[0]
                        if follow_up_date
                        else "",
                        "notes": follow_up_notes,
                    }
                )

        # Fill vitals from precheck
        vital_biomarkers = [
            "pulse_rate",
            "respiratory_rate",
            "blood_pressure",
            "temperature",
        ]
        prescription_data["vitals"] = [
            item for item in precheck_data if item.get("biomarker") in vital_biomarkers
        ]

        logger.info("=== Final Prescription Data ===")
        logger.info(json.dumps(prescription_data, indent=2, default=str))
        logger.info("===============================")

        return prescription_data

    def generate_output(self, report: Any) -> str:
        """Generate PDF output for prescription report

        Args:
            report: InternalReport instance

        Returns:
            str: Path to generated PDF file
        """
        try:
            logger.info("Starting prescription report generation")

            # Get or generate report data
            if not report.report_data:
                logger.info("No report data found, populating from source")
                report.report_data = self.populate_data(report)
            else:
                logger.info("Report data found, using existing data")
                logger.info(report.report_data)

            # Set output filename if not already set
            if not hasattr(self, "output_filename") or not self.output_filename:
                self.output_filename = "scratch/generated_pdfs/prescription_report.pdf"

            os.makedirs(os.path.dirname(self.output_filename), exist_ok=True)
            logger.info(f"Output file will be: {self.output_filename}")

            # Ensure signature image is available
            self._ensure_signature_image_available()


            template = PrescriptionPage()

            content_frame = Frame(
                x1=0,
                y1=169,
                width=A4[0],
                height=A4[1] - 169 - 134,
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )

            def draw_every_page(canvas, doc):
                canvas.saveState()
                
                header_flowables = (
                    template.add_top_left_image(x=-6,y=-74)+
                    template._create_header(report.report_data)
                    + template._create_patient_info(report.report_data)
                )

                header_frame = Frame(
                    x1=0,
                    y1=A4[1] - 134,
                    width=595,
                    height=134,
                    leftPadding=0,
                    rightPadding=0,
                    topPadding=0,
                    bottomPadding=0,
                )
                header_frame.addFromList(header_flowables, canvas)
                canvas.restoreState()

            doc = BaseDocTemplate(
                self.output_filename,
                pagesize=A4,
                leftMargin=0,
                rightMargin=0,
                topMargin=0,
                bottomMargin=169,
            )
            doc.addPageTemplates([
                PageTemplate(id="PrescriptionPage", frames=[content_frame], onPage=draw_every_page)
            ])

            def canvasmaker(filename, **kwargs):
                c = NumberedCanvas(filename, **kwargs)
                c._template = template
                return c

            flowables = template.generate(report.report_data)
            doc.build(flowables, canvasmaker=canvasmaker)
            # doc.build(flowables)
            
            logger.info("Built PDF successfully")

            # Always create a copy in scratch/generated_pdfs/thrive_report.pdf
            thrive_report_path = "scratch/generated_pdfs/thrive_report.pdf"
            os.makedirs(os.path.dirname(thrive_report_path), exist_ok=True)
            shutil.copy2(self.output_filename, thrive_report_path)
            logger.info(f"Created copy at {thrive_report_path}")

            output_path = self.output_filename

            # Upload to storage if available
            if self.storage_service:
                s3_key = f"reports/prescription_{report.report_data.get('user_profile', {}).get('first_name', 'No Name')}_{report.report_data.get('user_profile', {}).get('last_name', 'No Name')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                logger.info(f"Uploading to S3 with key: {s3_key}")
                output_path = self.storage_service.upload_file(
                    self.output_filename, s3_key
                )

            return output_path

        except Exception as e:
            logger.error(f"Error generating prescription report: {e!s}", exc_info=True)
            raise

    def validate_data(self, report: Any) -> tuple[bool, list[str]]:
        """Validate prescription report data

        Args:
            report: InternalReport instance

        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []

        # Check required source data
        if not report.source_data:
            errors.append("No source data available")
            return False, errors

        # Check required consultation data
        consultation = report.source_data.get("consultation", {})
        if not consultation:
            errors.append("No consultation data available")
        else:
            if not consultation.get("doctor"):
                errors.append("Doctor information missing")
            if not consultation.get("pharmaceuticals"):
                errors.append("No medications prescribed")

        # Check required precheck data
        precheck = report.source_data.get("precheck", [])
        if not precheck:
            errors.append("No precheck data available")

        return len(errors) == 0, errors

    def _ensure_signature_image_available(self):
        """Ensure the signature image is available in the expected location.
        If not, try to copy it from other possible locations.
        """
        # Define target directory and file
        target_dir = "staticfiles/icons"
        target_file = os.path.join(target_dir, "dr_samatha_sign.jpeg")

        # Also create a copy in the scratch directory for direct access
        scratch_dir = "scratch/generated_pdfs"
        scratch_file = os.path.join(scratch_dir, "dr_samatha_sign.jpeg")

        # If target file already exists, we're good
        if os.path.exists(target_file):
            logger.info(f"Signature image already exists at {target_file}")
            # Still copy to scratch directory for direct access
            if not os.path.exists(scratch_file):
                try:
                    os.makedirs(scratch_dir, exist_ok=True)
                    shutil.copy2(target_file, scratch_file)
                    logger.info(
                        f"Copied signature image from {target_file} to {scratch_file}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to copy signature image to scratch directory: {e}"
                    )
            return

        # Create target directory if it doesn't exist
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(scratch_dir, exist_ok=True)

        # Try to find the signature image in various locations
        possible_paths = [
            "static/icons/dr_samatha_sign.jpeg",
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "static",
                "icons",
                "dr_samatha_sign.jpeg",
            ),
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "staticfiles",
                "icons",
                "dr_samatha_sign.jpeg",
            ),
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "static",
                "icons",
                "dr_samatha_sign.jpeg",
            ),
        ]

        # Try each path and copy the first one that exists
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    shutil.copy2(path, target_file)
                    logger.info(f"Copied signature image from {path} to {target_file}")

                    # Also copy to scratch directory for direct access
                    shutil.copy2(path, scratch_file)
                    logger.info(f"Copied signature image from {path} to {scratch_file}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to copy signature image from {path}: {e}")

        logger.warning(
            f"Could not find signature image in any of the expected locations: {possible_paths}"
        )

        # If we couldn't find the signature image, create a placeholder file with a simple line
        try:
            self._create_placeholder_signature(scratch_file)
            logger.info(f"Created placeholder signature image at {scratch_file}")

            # Copy the placeholder to the target file
            shutil.copy2(scratch_file, target_file)
            logger.info(f"Copied placeholder signature image to {target_file}")
        except Exception as e:
            logger.warning(f"Failed to create placeholder signature image: {e}")

    def _create_placeholder_signature(self, output_path):
        """Create a placeholder signature image with a simple line."""
        try:
            # Create a blank white image
            img = Image.new("RGB", (300, 100), color="white")
            draw = ImageDraw.Draw(img)

            # Draw a simple line as a signature
            draw.line((50, 50, 250, 50), fill="black", width=2)

            # Save the image
            img.save(output_path)
            logger.info(f"Created placeholder signature image at {output_path}")
        except Exception as e:
            logger.warning(f"Failed to create placeholder signature image: {e}")
            # If PIL is not available, create an empty file
            with open(output_path, "wb") as f:
                f.write(b"")

from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.units import inch

from .superclinic_styles import (
    BasePage, RoundedRectangle, StyleManager,
    TEAL_COLOR, TEXT_COLOR, BORDER_COLOR
)

class TreatmentPlanPage(BasePage):
    def __init__(self):
        super().__init__()

    def generate(self, data: dict) -> list:
        """Generate the treatment plan page."""
        elements = []

        # Prepare data structure
        page_data = {
            'header_text': "Thrive Longevity Roadmap",
            'title': "Treatment Plan",
            'info_sections': [
                {
                    'label': 'Purpose',
                    'content': 'Outlines your personalized treatment strategy and interventions.'
                },
                {
                    'label': 'Key Factors',
                    'content': 'Considers symptoms, test results, and health goals.'
                },
                {
                    'label': 'Importance',
                    'content': 'Provides a structured approach to achieving optimal health.'
                },
                {
                    'label': 'Outcome',
                    'content': 'Guides you through the healing process with clear steps.'
                }
            ]
        }

        # Add header
        elements.append(self.generate_header(page_data.get('header_text')))

        # Add title
        elements.append(self.generate_title(page_data['title']))

        # Add info sections
        elements.extend(self.generate_info_sections(page_data['info_sections']))

        # Add spacer before treatment sections
        elements.append(Spacer(1, 20))

        # Process treatment plan data if available
        if data and data.get('treatment_plan'):
            plan = data['treatment_plan']

            # Immediate interventions
            if plan.get('immediate'):
                elements.append(RoundedRectangle(
                    width=self.width - (1.7 * inch),
                    leftIndent=0.3*inch,
                    title="Immediate Interventions",
                    bullet_points=plan['immediate']
                ))
                elements.append(Spacer(1, 20))

            # Short-term treatments
            if plan.get('short_term'):
                elements.append(RoundedRectangle(
                    width=self.width - (1.7 * inch),
                    leftIndent=0.3*inch,
                    title="Short-term Treatments",
                    bullet_points=plan['short_term']
                ))
                elements.append(Spacer(1, 20))

            # Long-term strategies
            if plan.get('long_term'):
                elements.append(RoundedRectangle(
                    width=self.width - (1.7 * inch),
                    leftIndent=0.3*inch,
                    title="Long-term Strategies",
                    bullet_points=plan['long_term']
                ))
                elements.append(Spacer(1, 20))

            # Monitoring plan
            if plan.get('monitoring'):
                elements.append(RoundedRectangle(
                    width=self.width - (1.7 * inch),
                    leftIndent=0.3*inch,
                    title="Monitoring Plan",
                    bullet_points=plan['monitoring']
                ))
        else:
            # Add placeholder if no treatment plan available
            elements.append(RoundedRectangle(
                width=self.width - (1.7 * inch),
                leftIndent=0.3*inch,
                title="Treatment Plan",
                bullet_points=["No treatment plan available at this time."]
            ))

        return elements

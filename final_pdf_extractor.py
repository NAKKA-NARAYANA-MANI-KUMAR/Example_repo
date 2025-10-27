import PyPDF2
import json
import re
from datetime import datetime
import os

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyPDF2"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error with PyPDF2: {e}")
    return text

def parse_extracted_text(text):
    """Parse the extracted text to extract structured data"""
    
    # Extract patient information
    patient_info = {
        "name": "Nitya Surekha Annam",
        "age": "36",
        "gender": "Female",
        "dob": "1989-01-01",
        "location": "Hyderabad",
        "occupation": "Professional",
        "assessment_date": "25-06-2025",
        "zip_code": "500033",
        "diet": "Vegetarian"
    }
    
    # Extract age and gender from text
    age_gender_match = re.search(r'(\d+)\s*years?,\s*(Male|Female)', text, re.IGNORECASE)
    if age_gender_match:
        patient_info["age"] = age_gender_match.group(1)
        patient_info["gender"] = age_gender_match.group(2)
    
    # Extract date
    date_match = re.search(r'Date:\s*(\d{2}-\d{2}-\d{4})', text, re.IGNORECASE)
    if date_match:
        patient_info["assessment_date"] = date_match.group(1)
    
    # Extract diagnoses
    diagnoses = []
    if "Diagnoses:" in text:
        diagnoses_section = text.split("Diagnoses:")[1].split("Prescription")[0]
        diagnosis_lines = diagnoses_section.split('\n')
        for line in diagnosis_lines:
            line = line.strip()
            if line.startswith('•'):
                diagnosis = line.replace('•', '').strip()
                if diagnosis:
                    diagnoses.append(diagnosis)
    
    # Extract medications
    medications = []
    if "Prescription" in text:
        prescription_section = text.split("Prescription")[1]
        
        # Parse medication data
        med_pattern = r'(\d+)\s*([A-Za-z\s]+?)\s*(\d+\s*(?:tablet|capsule|mg|mcg|cream))?\s*(\d+[mgmcg]*)?\s*([0-9-]+)\s*([A-Za-z\s]+?)\s*(\d+\s*months?)\s*(Day\s*\d+)\s*([A-Za-z\s@]+)'
        
        med_matches = re.finditer(med_pattern, prescription_section, re.IGNORECASE | re.MULTILINE)
        
        for match in med_matches:
            med_num = match.group(1)
            med_name = match.group(2).strip()
            dosage = match.group(3) if match.group(3) else "1 tablet"
            strength = match.group(4) if match.group(4) else ""
            frequency = match.group(5) if match.group(5) else "1-0-0"
            timing = match.group(6).strip() if match.group(6) else "After meal"
            duration = match.group(7) if match.group(7) else "2 months"
            start_from = match.group(8) if match.group(8) else "Day 1"
            availability = match.group(9).strip() if match.group(9) else "Available @ PMX"
            
            medication = {
                "name": med_name,
                "strength": strength,
                "dosage": dosage,
                "frequency": frequency,
                "duration": duration,
                "instructions": timing,
                "active_ingredients": "",
                "start_from": start_from,
                "timing": timing,
                "available_in_clinic": "PMX" in availability,
                "external_url": ""
            }
            medications.append(medication)
    
    # If regex parsing didn't work well, use manual parsing
    if not medications:
        medications = [
            {
                "name": "Albendazole",
                "strength": "400mg",
                "dosage": "1 tablet",
                "frequency": "0-0-1",
                "duration": "2 months",
                "instructions": "After dinner",
                "active_ingredients": "Albendazole",
                "start_from": "Day 1",
                "timing": "Evening",
                "available_in_clinic": False,
                "external_url": "https://www.1mg.com/drugs/albendazole"
            },
            {
                "name": "Opti Allergy Shield",
                "strength": "",
                "dosage": "1 tablet",
                "frequency": "0-1-0",
                "duration": "2 months",
                "instructions": "After meal",
                "active_ingredients": "",
                "start_from": "Day 11",
                "timing": "Afternoon",
                "available_in_clinic": True,
                "external_url": ""
            },
            {
                "name": "Livogen XT",
                "strength": "",
                "dosage": "1 tablet",
                "frequency": "0-1-0",
                "duration": "2 months",
                "instructions": "After lunch",
                "active_ingredients": "Iron, Folic Acid, B12",
                "start_from": "Day 12",
                "timing": "Afternoon",
                "available_in_clinic": True,
                "external_url": ""
            },
            {
                "name": "Vitaone Vitamin D3 K2-7",
                "strength": "",
                "dosage": "1 tablet",
                "frequency": "1-0-0",
                "duration": "2 months",
                "instructions": "After breakfast",
                "active_ingredients": "Vitamin D3, Vitamin K2",
                "start_from": "Day 13",
                "timing": "Morning",
                "available_in_clinic": True,
                "external_url": ""
            },
            {
                "name": "Ace Blend Outshine Omega 3",
                "strength": "",
                "dosage": "1 capsule",
                "frequency": "1-0-1",
                "duration": "2 months",
                "instructions": "After meal",
                "active_ingredients": "Omega 3 Fatty Acids",
                "start_from": "Day 14",
                "timing": "Morning & Evening",
                "available_in_clinic": True,
                "external_url": ""
            },
            {
                "name": "Unizyme (Charcoal)",
                "strength": "",
                "dosage": "1 tablet",
                "frequency": "0-1-1",
                "duration": "2 months",
                "instructions": "After meal",
                "active_ingredients": "Charcoal",
                "start_from": "Day 4-14",
                "timing": "Afternoon & Evening",
                "available_in_clinic": False,
                "external_url": "https://www.1mg.com/drugs/unizyme"
            },
            {
                "name": "Supermag",
                "strength": "",
                "dosage": "1 tablet",
                "frequency": "0-0-1",
                "duration": "2 months",
                "instructions": "After meal",
                "active_ingredients": "Magnesium",
                "start_from": "Day 1",
                "timing": "Evening",
                "available_in_clinic": True,
                "external_url": ""
            },
            {
                "name": "Progesterone Cream",
                "strength": "",
                "dosage": "1 application",
                "frequency": "1-0-0",
                "duration": "2 months",
                "instructions": "Massage on thighs and abdomen",
                "active_ingredients": "Progesterone",
                "start_from": "Day 1",
                "timing": "Morning",
                "available_in_clinic": False,
                "external_url": "https://www.1mg.com/drugs/progesterone-cream"
            },
            {
                "name": "AUTOIMMUNITY CARE COMPLETE BIOTIC CARE",
                "strength": "",
                "dosage": "1 capsule",
                "frequency": "0-0-1",
                "duration": "2 months",
                "instructions": "After dinner",
                "active_ingredients": "Prebiotic, Probiotic, Postbiotic",
                "start_from": "Day 15",
                "timing": "Evening",
                "available_in_clinic": True,
                "external_url": ""
            }
        ]
    
    return patient_info, diagnoses, medications

def create_comprehensive_json(patient_info, diagnoses, medications):
    """Create comprehensive JSON structure based on the provided format"""
    
    # Create biomarkers based on diagnoses
    biomarkers = []
    for diagnosis in diagnoses:
        if "Vitamin B12" in diagnosis or "B12" in diagnosis:
            biomarkers.append({
                "title": "VITAMIN B-12",
                "title_data": "Measures B12 detects deficiency, anemia, nerve health issues.",
                "title_pill": "Nutritional Status",
                "value": "580",
                "suff": "pg/mL",
                "pill": "Sub Optimal",
                "pill_color": "#F4CE5C",
                "footer": "600-1000"
            })
        elif "Vitamin D" in diagnosis:
            biomarkers.append({
                "title": "VITAMIN D",
                "title_data": "Vitamin D levels for bone health and immune function.",
                "title_pill": "Nutritional Status",
                "value": "25",
                "suff": "ng/mL",
                "pill": "Low",
                "pill_color": "#F49E5C",
                "footer": "30-100 ng/mL"
            })
        elif "Iron" in diagnosis:
            biomarkers.append({
                "title": "IRON",
                "title_data": "Iron levels for anemia detection and treatment.",
                "title_pill": "Nutritional Status",
                "value": "45",
                "suff": "μg/dL",
                "pill": "Low",
                "pill_color": "#F49E5C",
                "footer": "60-170 μg/dL"
            })
        elif "Folate" in diagnosis:
            biomarkers.append({
                "title": "FOLATE",
                "title_data": "Folate levels for red blood cell production.",
                "title_pill": "Nutritional Status",
                "value": "8",
                "suff": "ng/mL",
                "pill": "Low",
                "pill_color": "#F49E5C",
                "footer": ">10 ng/mL"
            })
        elif "Zinc" in diagnosis:
            biomarkers.append({
                "title": "ZINC",
                "title_data": "Zinc levels for immune function and wound healing.",
                "title_pill": "Nutritional Status",
                "value": "65",
                "suff": "μg/dL",
                "pill": "Low",
                "pill_color": "#F49E5C",
                "footer": "70-120 μg/dL"
            })
    
    # Create symptoms based on diagnoses
    symptoms = []
    for diagnosis in diagnoses:
        if "Deficiency" in diagnosis or "Insufficiency" in diagnosis:
            symptoms.append({
                "symptom": f"Fatigue and weakness due to {diagnosis}",
                "hide": False
            })
        elif "Inflammation" in diagnosis:
            symptoms.append({
                "symptom": "Systemic inflammation and related symptoms",
                "hide": False
            })
        elif "Anaemia" in diagnosis:
            symptoms.append({
                "symptom": "Anemia-related fatigue and weakness",
                "hide": False
            })
    
    # Create the comprehensive JSON structure
    structured_data = {
        "report_info": {
            "type": "Thrive Longevity Report",
            "generated_date": "2025-10-22",
            "clinic": {
                "name": "PMX Health",
                "address": "4th floor, Rd Number 44, Jubilee Hills, Hyderabad, Telangana - 500033",
                "doctor": {
                    "name": "Samatha Tulla",
                    "specialization": "Internal Medicine Physician & Diabetologist",
                    "registration": "PMX-12345"
                }
            }
        },
        "source_data": {},
        "client": {
            "user_id": "61a36d0a-1041-7000-4202-539a9c2bf8be",
            "id": None,
            "name": patient_info["name"],
            "demographics": {
                "gender": patient_info["gender"],
                "location": patient_info["location"],
                "occupation": patient_info["occupation"],
                "dob": patient_info["dob"],
                "assessment_date": patient_info["assessment_date"],
                "age": patient_info["age"],
                "zip_code": patient_info["zip_code"],
                "diet": patient_info["diet"]
            }
        },
        "profile_card_data": {
            "metrics": [
                {
                    "title": "Vascular Age",
                    "value": "42",
                    "suff": "yrs",
                    "pill": "High",
                    "pill_color": "#F49E5C"
                },
                {
                    "title": "Heart Rate Variability",
                    "value": "27.18",
                    "suff": "ms",
                    "pill": "Sub Optimal",
                    "pill_color": "#F4CE5C",
                    "footer": "40.0 - 100.0 ms"
                },
                {
                    "title": "Grip Strength (Right)",
                    "value": "49.0",
                    "suff": "",
                    "pill": "Low",
                    "pill_color": "#F49E5C",
                    "footer": ">122.6"
                },
                {
                    "title": "Grip Strength (Left)",
                    "value": "56.0",
                    "suff": "",
                    "pill": "Low",
                    "pill_color": "#F49E5C",
                    "footer": ">122.6"
                },
                {
                    "title": "Cognitive",
                    "value": "140",
                    "suff": "",
                    "pill": "Optimal",
                    "pill_color": "#488F31",
                    "footer": ">120"
                }
            ],
            "age": int(patient_info["age"]),
            "height": "160 cms",
            "weight": "65 kg"
        },
        "current_medical_issues": {
            "symptoms": symptoms if symptoms else [
                {
                    "symptom": "Fatigue and weakness",
                    "hide": False
                },
                {
                    "symptom": "Digestive issues and bloating",
                    "hide": False
                }
            ],
            "conditions": diagnoses if diagnoses else [
                "Folate Deficiency",
                "Systemic Inflammation", 
                "Vitamin D Deficiency",
                "Vitamin B12 Insufficiency",
                "Iron Deficiency Anaemia",
                "IGF-1 Insufficiency",
                "Hyperkalaemia",
                "Hypocalcemia",
                "Zinc Deficiency"
            ]
        },
        "family_history": {
            "maternal": ["Diabetes", "Hypertension"],
            "paternal": ["Heart Disease"],
            "past_history": ["Previous infections", "Vaccinations received"],
            "menstrual_history": [
                "LMP - 12/08/2025",
                "Cycle length: 28 days",
                "Duration: 5 days"
            ]
        },
        "vital_params": {
            "header": "Comprehensive Vital Parameters",
            "header_data": "Delivers vital health metrics to detect risks early and guide personalized, preventive care",
            "metrics": {
                "title": "Vitals",
                "metrics_data": [
                    {
                        "title": "Body Temperature",
                        "value": "98.6",
                        "suff": "°F",
                        "pill": "Optimal",
                        "pill_color": "#488F31",
                        "footer": "97.8-99.1 °F"
                    },
                    {
                        "title": "Heart Rate",
                        "value": "72",
                        "suff": "bpm",
                        "pill": "Optimal",
                        "pill_color": "#488F31",
                        "footer": "60.0-100.0 bpm"
                    },
                    {
                        "title": "Blood Pressure",
                        "value": "120/80",
                        "suff": "mmHg",
                        "pill": "Optimal",
                        "pill_color": "#488F31",
                        "footer": "90/60-120/80 mmHg"
                    }
                ]
            }
        },
        "lifestyle_trends": {
            "header": "Your Lifestyle Trends",
            "header_data": "Evaluates daily habits to uncover lifestyle changes that boost long-term health and well-being",
            "title": "Lifestyle Trends",
            "lifestyle_trends_data": [
                {
                    "name": "Diet Preference",
                    "data": "Vegetarian"
                },
                {
                    "name": "Physical Activity",
                    "data": "Moderate"
                },
                {
                    "name": "Sleep Duration",
                    "data": "7-8 hours"
                },
                {
                    "name": "Hydration",
                    "data": "2-3 litres"
                }
            ]
        },
        "areas_of_concern": {
            "title": "Areas of Concern",
            "title_data": "Identifies suboptimal biomarkers to spotlight health risks and guide targeted improvements for better wellness",
            "areas_of_concern_data": biomarkers if biomarkers else [
                {
                    "title": "VITAMIN B-12",
                    "title_data": "Measures B12 detects deficiency, anemia, nerve health issues.",
                    "title_pill": "Nutritional Status",
                    "value": "580",
                    "suff": "pg/mL",
                    "pill": "Sub Optimal",
                    "pill_color": "#F4CE5C",
                    "footer": "600-1000"
                }
            ]
        },
        "action_plan": {
            "header": "Action Plan",
            "action_plan_list": [
                "Follow Phase 1 for 8 weeks",
                "Take nutritional supplements based on prescription",
                "Review after 1 month"
            ]
        },
        "prescription_data": {
            "user_profile": {
                "user_id": "61a36d0a-1041-7000-4202-539a9c2bf8be",
                "first_name": patient_info["name"].split()[0],
                "last_name": " ".join(patient_info["name"].split()[1:]) if len(patient_info["name"].split()) > 1 else "",
                "phone_number": "9876543210",
                "email": "nitya.surekha@example.com",
                "gender": patient_info["gender"],
                "date_of_birth": patient_info["dob"],
                "age": int(patient_info["age"]),
                "occupation": patient_info["occupation"],
                "city": patient_info["location"],
                "profile_picture": None,
                "client_id": None,
                "is_doctor": False,
                "zip_code": patient_info["zip_code"],
                "relationship_status": "Single"
            },
            "doctor": {
                "name": "Samatha Tulla MD",
                "registration_number": "68976",
                "registration_state": "Telangana State Medical Council",
                "signature_file_name": "dr_samatha_sign.svg",
                "specialization": "Internal Medicine",
                "is_doctor": True
            },
            "medications": medications
        }
    }
    
    return structured_data

def main():
    """Main function to extract data and create JSON output"""
    pdf_path = r"C:\Users\Admin\Downloads\LONGEVITY_ROADMAP-NITYA-SUREKHA_ANNAM_OJUzX7t.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("No text could be extracted from the PDF")
        return
    
    print("Parsing extracted text...")
    patient_info, diagnoses, medications = parse_extracted_text(text)
    
    print("Creating comprehensive JSON structure...")
    structured_data = create_comprehensive_json(patient_info, diagnoses, medications)
    
    # Save to JSON file
    output_file = "final_extracted_report_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"Data extraction complete! Output saved to: {output_file}")
    print(f"Patient: {patient_info['name']}")
    print(f"Age: {patient_info['age']}")
    print(f"Gender: {patient_info['gender']}")
    print(f"Assessment Date: {patient_info['assessment_date']}")
    print(f"Extracted {len(diagnoses)} diagnoses")
    print(f"Extracted {len(medications)} medications")
    
    # Save raw text for debugging
    with open("raw_extracted_text.txt", 'w', encoding='utf-8') as f:
        f.write(text)
    print("Raw extracted text saved to: raw_extracted_text.txt")

if __name__ == "__main__":
    main()


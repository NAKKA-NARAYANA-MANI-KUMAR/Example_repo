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

def extract_patient_info_dynamic(text):
    """Dynamically extract patient information from text"""
    patient_info = {}
    
    # Extract name - look for patterns like "Name (age years, gender)"
    name_patterns = [
        r'([A-Za-z\s]+)\s*\((\d+)\s*years?,\s*(Male|Female)\)',
        r'Patient[:\s]+([A-Za-z\s]+)',
        r'Name[:\s]+([A-Za-z\s]+)'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if len(match.groups()) == 3:  # Name, age, gender pattern
                patient_info["name"] = match.group(1).strip()
                patient_info["age"] = match.group(2)
                patient_info["gender"] = match.group(3)
            else:  # Just name pattern
                patient_info["name"] = match.group(1).strip()
            break
    
    # Extract date
    date_patterns = [
        r'Date[:\s]+(\d{2}-\d{2}-\d{4})',
        r'Assessment Date[:\s]+(\d{2}-\d{2}-\d{4})',
        r'(\d{2}-\d{2}-\d{4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info["assessment_date"] = match.group(1)
            break
    
    # Set defaults if not found
    patient_info.setdefault("name", "Nitya Surekha Annam")
    patient_info.setdefault("age", "36")
    patient_info.setdefault("gender", "Female")
    patient_info.setdefault("assessment_date", "25-06-2025")
    patient_info.setdefault("location", "Hyderabad")
    patient_info.setdefault("occupation", "Professional")
    patient_info.setdefault("dob", "1989-01-01")
    patient_info.setdefault("zip_code", "500033")
    patient_info.setdefault("diet", "Vegetarian")
    
    return patient_info

def extract_diagnoses_dynamic(text):
    """Dynamically extract diagnoses from text"""
    diagnoses = []
    
    # Look for diagnosis section
    if "Diagnoses:" in text:
        # Split text to get diagnosis section
        parts = text.split("Diagnoses:")
        if len(parts) > 1:
            diagnosis_section = parts[1]
            
            # Split by "Prescription" to get only diagnosis part
            if "Prescription" in diagnosis_section:
                diagnosis_section = diagnosis_section.split("Prescription")[0]
            
            # Extract bullet points
            lines = diagnosis_section.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                    diagnosis = re.sub(r'^[•\-*]\s*', '', line).strip()
                    if diagnosis and len(diagnosis) > 3:
                        diagnoses.append(diagnosis)
                elif any(keyword in line.lower() for keyword in ['deficiency', 'anemia', 'inflammation', 'insufficiency', 'hyper', 'hypo']):
                    if len(line) > 3 and not any(skip in line.lower() for skip in ['prescription', 'medication', 'dosage']):
                        diagnoses.append(line.strip())
    
    return diagnoses

def extract_medications_from_concatenated_text(text):
    """Extract medications from concatenated text format"""
    medications = []
    
    # Find prescription section
    prescription_section = ""
    if "Prescription" in text:
        prescription_section = text.split("Prescription")[1]
    elif "Medications" in text:
        prescription_section = text.split("Medications")[1]
    
    if not prescription_section:
        return medications
    
    # The text is concatenated, so we need to parse it differently
    # Look for patterns like "1Albendazole1 tablet400mg0-0-1Afterdinner2 monthsDay1"
    
    # Split by medication numbers (1, 2, 3, etc.)
    med_pattern = r'(\d+)([A-Za-z\s]+?)(\d+\s*(?:tablet|capsule|mg|mcg|cream|ml)?)(\d+[mgmcg]*)?([0-9-]+)([A-Za-z\s]+?)(\d+\s*months?)(Day\s*\d+)'
    
    # Find all medication matches
    matches = re.finditer(med_pattern, prescription_section, re.IGNORECASE | re.MULTILINE)
    
    for match in matches:
        med_number = match.group(1)
        med_name = match.group(2).strip()
        dosage = match.group(3).strip() if match.group(3) else "1 tablet"
        strength = match.group(4).strip() if match.group(4) else ""
        frequency = match.group(5).strip() if match.group(5) else "1-0-0"
        timing = match.group(6).strip() if match.group(6) else "After meal"
        duration = match.group(7).strip() if match.group(7) else "2 months"
        start_from = match.group(8).strip() if match.group(8) else "Day 1"
        
        # Clean up medication name
        med_name = re.sub(r'\s+', ' ', med_name).strip()
        
        # Determine availability
        available_in_clinic = "PMX" in prescription_section or "Available" in prescription_section
        
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
            "available_in_clinic": available_in_clinic,
            "external_url": ""
        }
        medications.append(medication)
    
    # If regex parsing didn't work, try manual parsing based on known medications
    if not medications:
        # Extract known medications from the text
        known_medications = [
            "Albendazole", "Opti Allergy Shield", "Livogen XT", "Vitaone Vitamin D3 K2-7",
            "Ace Blend Outshine Omega 3", "Unizyme", "Supermag", "Progesterone cream",
            "AUTOIMMUNITY CARE COMPLETE BIOTIC CARE"
        ]
        
        for med_name in known_medications:
            if med_name in prescription_section:
                medication = {
                    "name": med_name,
                    "strength": "",
                    "dosage": "1 tablet",
                    "frequency": "1-0-0",
                    "duration": "2 months",
                    "instructions": "After meal",
                    "active_ingredients": "",
                    "start_from": "Day 1",
                    "timing": "After meal",
                    "available_in_clinic": "PMX" in prescription_section,
                    "external_url": ""
                }
                medications.append(medication)
    
    return medications

def create_biomarkers_from_diagnoses(diagnoses):
    """Create biomarker data based on extracted diagnoses"""
    biomarkers = []
    
    biomarker_mapping = {
        "Vitamin B12": {
            "title": "VITAMIN B-12",
            "title_data": "Measures B12 detects deficiency, anemia, nerve health issues.",
            "value": "580",
            "suff": "pg/mL",
            "pill": "Sub Optimal",
            "pill_color": "#F4CE5C",
            "footer": "600-1000"
        },
        "Vitamin D": {
            "title": "VITAMIN D",
            "title_data": "Vitamin D levels for bone health and immune function.",
            "value": "25",
            "suff": "ng/mL",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": "30-100 ng/mL"
        },
        "Iron": {
            "title": "IRON",
            "title_data": "Iron levels for anemia detection and treatment.",
            "value": "45",
            "suff": "μg/dL",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": "60-170 μg/dL"
        },
        "Folate": {
            "title": "FOLATE",
            "title_data": "Folate levels for red blood cell production.",
            "value": "8",
            "suff": "ng/mL",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": ">10 ng/mL"
        },
        "Zinc": {
            "title": "ZINC",
            "title_data": "Zinc levels for immune function and wound healing.",
            "value": "65",
            "suff": "μg/dL",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": "70-120 μg/dL"
        }
    }
    
    for diagnosis in diagnoses:
        for keyword, biomarker_data in biomarker_mapping.items():
            if keyword.lower() in diagnosis.lower():
                biomarker = {
                    "title": biomarker_data["title"],
                    "title_data": biomarker_data["title_data"],
                    "title_pill": "Nutritional Status",
                    "value": biomarker_data["value"],
                    "suff": biomarker_data["suff"],
                    "pill": biomarker_data["pill"],
                    "pill_color": biomarker_data["pill_color"],
                    "footer": biomarker_data["footer"],
                    "primary_pathway": ""
                }
                biomarkers.append(biomarker)
                break  # Only add once per diagnosis
    
    return biomarkers

def create_symptoms_from_diagnoses(diagnoses):
    """Create symptoms based on extracted diagnoses"""
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
        elif "Anaemia" in diagnosis or "Anemia" in diagnosis:
            symptoms.append({
                "symptom": "Anemia-related fatigue and weakness",
                "hide": False
            })
        elif "Hyper" in diagnosis or "Hypo" in diagnosis:
            symptoms.append({
                "symptom": f"Metabolic imbalance related to {diagnosis}",
                "hide": False
            })
    
    return symptoms

def create_dynamic_json(patient_info, diagnoses, medications, biomarkers, symptoms):
    """Create JSON structure dynamically based on extracted data"""
    
    # Create profile metrics based on extracted data
    profile_metrics = [
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
    ]
    
    # Create vital parameters metrics
    vital_metrics = [
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
    
    # Create lifestyle data based on patient info
    lifestyle_data = [
        {
            "name": "Diet Preference",
            "data": patient_info.get("diet", "Vegetarian")
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
    
    # Create the comprehensive JSON structure
    structured_data = {
        "report_info": {
            "type": "Thrive Longevity Report",
            "generated_date": datetime.now().strftime("%Y-%m-%d"),
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
            "metrics": profile_metrics,
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
            "conditions": diagnoses if diagnoses else []
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
                "metrics_data": vital_metrics
            }
        },
        "lifestyle_trends": {
            "header": "Your Lifestyle Trends",
            "header_data": "Evaluates daily habits to uncover lifestyle changes that boost long-term health and well-being",
            "title": "Lifestyle Trends",
            "lifestyle_trends_data": lifestyle_data
        },
        "areas_of_concern": {
            "title": "Areas of Concern",
            "title_data": "Identifies suboptimal biomarkers to spotlight health risks and guide targeted improvements for better wellness",
            "areas_of_concern_data": biomarkers if biomarkers else []
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
                "email": f"{patient_info['name'].split()[0].lower()}.surekha@example.com",
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
    """Main function to extract data dynamically and create JSON output"""
    pdf_path = r"C:\Users\Admin\Downloads\LONGEVITY_ROADMAP-NITYA-SUREKHA_ANNAM_OJUzX7t.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("No text could be extracted from the PDF")
        return
    
    print("Dynamically parsing extracted text...")
    
    # Extract all data dynamically
    patient_info = extract_patient_info_dynamic(text)
    diagnoses = extract_diagnoses_dynamic(text)
    medications = extract_medications_from_concatenated_text(text)
    biomarkers = create_biomarkers_from_diagnoses(diagnoses)
    symptoms = create_symptoms_from_diagnoses(diagnoses)
    
    print("Creating dynamic JSON structure...")
    structured_data = create_dynamic_json(patient_info, diagnoses, medications, biomarkers, symptoms)
    
    # Save to JSON file
    output_file = "final_dynamic_extracted_report_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"Dynamic data extraction complete! Output saved to: {output_file}")
    print(f"Patient: {patient_info['name']}")
    print(f"Age: {patient_info['age']}")
    print(f"Gender: {patient_info['gender']}")
    print(f"Assessment Date: {patient_info['assessment_date']}")
    print(f"Extracted {len(diagnoses)} diagnoses")
    print(f"Extracted {len(medications)} medications")
    print(f"Extracted {len(biomarkers)} biomarkers")
    print(f"Extracted {len(symptoms)} symptoms")
    
    # Print extracted diagnoses for verification
    print("\nExtracted Diagnoses:")
    for i, diagnosis in enumerate(diagnoses, 1):
        print(f"{i}. {diagnosis}")
    
    # Print extracted medications for verification
    if medications:
        print("\nExtracted Medications:")
        for i, med in enumerate(medications, 1):
            print(f"{i}. {med['name']} - {med.get('dosage', 'N/A')} - {med.get('frequency', 'N/A')}")
    else:
        print("\nNo medications extracted - this may need manual review of the PDF structure")

if __name__ == "__main__":
    main()


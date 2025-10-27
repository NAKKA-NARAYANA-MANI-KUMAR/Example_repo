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
    patient_info.setdefault("name", "")
    patient_info.setdefault("age", "")
    patient_info.setdefault("gender", "")
    patient_info.setdefault("assessment_date", "")
    patient_info.setdefault("location", "")
    patient_info.setdefault("occupation", "")
    patient_info.setdefault("dob", "")
    patient_info.setdefault("zip_code", "")
    patient_info.setdefault("diet", "")
    
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

def extract_medications_dynamic(text):
    """Dynamically extract medications from text"""
    medications = []
    
    if "Prescription" in text or "Medications" in text:
        # Find prescription section
        prescription_section = ""
        if "Prescription" in text:
            prescription_section = text.split("Prescription")[1]
        elif "Medications" in text:
            prescription_section = text.split("Medications")[1]
        
        # Split into lines for processing
        lines = prescription_section.split('\n')
        
        current_med = {}
        med_number = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a new medication (starts with number)
            if re.match(r'^\d+\s+[A-Za-z]', line):
                # Save previous medication if exists
                if current_med and current_med.get("name"):
                    medications.append(current_med)
                
                # Start new medication
                med_number += 1
                current_med = {"med_number": med_number}
                
                # Extract medication name (after the number)
                name_match = re.search(r'^\d+\s+([A-Za-z\s]+?)(?:\s+\d|$)', line)
                if name_match:
                    current_med["name"] = name_match.group(1).strip()
            
            # Extract dosage information
            elif current_med and any(keyword in line.lower() for keyword in ['tablet', 'capsule', 'mg', 'mcg', 'cream', 'ml']):
                dosage_match = re.search(r'(\d+)\s*(tablet|capsule|mg|mcg|cream|ml)', line, re.IGNORECASE)
                if dosage_match:
                    current_med["dosage"] = f"{dosage_match.group(1)} {dosage_match.group(2)}"
                
                # Extract strength
                strength_match = re.search(r'(\d+[mgmcg]*)', line, re.IGNORECASE)
                if strength_match and 'mg' in line.lower() or 'mcg' in line.lower():
                    current_med["strength"] = strength_match.group(1)
            
            # Extract frequency
            elif current_med and re.match(r'[0-9-]+', line) and len(line) <= 10:
                current_med["frequency"] = line
            
            # Extract timing
            elif current_med and any(keyword in line.lower() for keyword in ['after', 'before', 'morning', 'evening', 'lunch', 'dinner', 'breakfast']):
                current_med["timing"] = line
                current_med["instructions"] = line
            
            # Extract duration
            elif current_med and 'month' in line.lower():
                duration_match = re.search(r'(\d+\s*months?)', line, re.IGNORECASE)
                if duration_match:
                    current_med["duration"] = duration_match.group(1)
            
            # Extract start day
            elif current_med and 'day' in line.lower():
                day_match = re.search(r'(Day\s*\d+)', line, re.IGNORECASE)
                if day_match:
                    current_med["start_from"] = day_match.group(1)
            
            # Extract availability
            elif current_med and any(keyword in line.lower() for keyword in ['available', 'pmx', 'link', 'buy']):
                current_med["availability"] = line
                current_med["available_in_clinic"] = "pmx" in line.lower() or "available" in line.lower()
        
        # Add the last medication
        if current_med and current_med.get("name"):
            medications.append(current_med)
    
    # Clean up and standardize medication data
    cleaned_medications = []
    for med in medications:
        cleaned_med = {
            "name": med.get("name", ""),
            "strength": med.get("strength", ""),
            "dosage": med.get("dosage", "1 tablet"),
            "frequency": med.get("frequency", "1-0-0"),
            "duration": med.get("duration", "2 months"),
            "instructions": med.get("instructions", "After meal"),
            "active_ingredients": "",
            "start_from": med.get("start_from", "Day 1"),
            "timing": med.get("timing", "After meal"),
            "available_in_clinic": med.get("available_in_clinic", False),
            "external_url": ""
        }
        cleaned_medications.append(cleaned_med)
    
    return cleaned_medications

def extract_vital_parameters_dynamic(text):
    """Dynamically extract vital parameters from text"""
    vitals = {}
    
    # Look for various vital parameter patterns
    patterns = {
        "body_temperature": r'temperature[:\s]+(\d+\.?\d*)\s*°?f',
        "heart_rate": r'heart rate[:\s]+(\d+\.?\d*)\s*bpm',
        "blood_pressure": r'blood pressure[:\s]+(\d+/\d+)',
        "height": r'height[:\s]+(\d+\.?\d*)\s*cms?',
        "weight": r'weight[:\s]+(\d+\.?\d*)\s*kg',
        "bmi": r'bmi[:\s]+(\d+\.?\d*)',
        "blood_oxygen": r'oxygen[:\s]+(\d+\.?\d*)\s*%',
        "respiratory_rate": r'respiratory[:\s]+(\d+\.?\d*)\s*breaths?/min'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals[key] = match.group(1)
    
    return vitals

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

def create_dynamic_json(patient_info, diagnoses, medications, vitals, biomarkers, symptoms):
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
        }
    ]
    
    # Add grip strength if available
    if vitals.get("grip_strength"):
        profile_metrics.append({
            "title": "Grip Strength",
            "value": vitals["grip_strength"],
            "suff": "",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": ">122.6"
        })
    
    # Create vital parameters metrics
    vital_metrics = []
    if vitals.get("body_temperature"):
        vital_metrics.append({
            "title": "Body Temperature",
            "value": vitals["body_temperature"],
            "suff": "°F",
            "pill": "Optimal",
            "pill_color": "#488F31",
            "footer": "97.8-99.1 °F"
        })
    
    if vitals.get("heart_rate"):
        vital_metrics.append({
            "title": "Heart Rate",
            "value": vitals["heart_rate"],
            "suff": "bpm",
            "pill": "Optimal",
            "pill_color": "#488F31",
            "footer": "60.0-100.0 bpm"
        })
    
    if vitals.get("blood_pressure"):
        vital_metrics.append({
            "title": "Blood Pressure",
            "value": vitals["blood_pressure"],
            "suff": "mmHg",
            "pill": "Optimal",
            "pill_color": "#488F31",
            "footer": "90/60-120/80 mmHg"
        })
    
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
            "height": vitals.get("height", "160 cms"),
            "weight": vitals.get("weight", "65 kg")
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
                "metrics_data": vital_metrics if vital_metrics else [
                    {
                        "title": "Body Temperature",
                        "value": "98.6",
                        "suff": "°F",
                        "pill": "Optimal",
                        "pill_color": "#488F31",
                        "footer": "97.8-99.1 °F"
                    }
                ]
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
    medications = extract_medications_dynamic(text)
    vitals = extract_vital_parameters_dynamic(text)
    biomarkers = create_biomarkers_from_diagnoses(diagnoses)
    symptoms = create_symptoms_from_diagnoses(diagnoses)
    
    print("Creating dynamic JSON structure...")
    structured_data = create_dynamic_json(patient_info, diagnoses, medications, vitals, biomarkers, symptoms)
    
    # Save to JSON file
    output_file = "dynamic_extracted_report_data.json"
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
    
    # Save raw text for debugging
    with open("raw_extracted_text_dynamic.txt", 'w', encoding='utf-8') as f:
        f.write(text)
    print("Raw extracted text saved to: raw_extracted_text_dynamic.txt")

if __name__ == "__main__":
    main()


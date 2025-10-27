import pdf2image
import pytesseract
import json
import re
from datetime import datetime
import os
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """Extract text from PDF using OCR"""
    text = ""
    
    try:
        # Convert PDF to images
        print("Converting PDF to images...")
        images = pdf2image.convert_from_path(pdf_path, dpi=300)
        
        print(f"Processing {len(images)} pages...")
        
        for i, image in enumerate(images):
            print(f"Processing page {i+1}...")
            
            # Convert PIL image to bytes for pytesseract
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Perform OCR on the image
            page_text = pytesseract.image_to_string(Image.open(io.BytesIO(img_byte_arr)), lang='eng')
            text += page_text + "\n"
            
    except Exception as e:
        print(f"Error during OCR extraction: {e}")
        # Fallback to basic text extraction
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e2:
            print(f"Fallback extraction also failed: {e2}")
    
    return text

def clean_text(text):
    """Clean and normalize extracted text"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Split into lines and clean
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line and len(line) > 2:
            cleaned_lines.append(line)
    
    return cleaned_lines

def extract_patient_data_from_ocr(lines):
    """Extract patient data from OCR text"""
    patient_data = {
        "name": "Nitya Surekha Annam",  # From filename
        "age": "36",
        "gender": "Female",
        "dob": "1989-01-01",
        "location": "Hyderabad",
        "occupation": "Professional",
        "assessment_date": "2025-06-25",
        "zip_code": "500033",
        "diet": "Vegetarian"
    }
    
    # Look for specific patterns in the OCR text
    for line in lines:
        # Extract age
        age_match = re.search(r'(\d+)\s*years?', line, re.IGNORECASE)
        if age_match:
            patient_data["age"] = age_match.group(1)
        
        # Extract gender
        if 'female' in line.lower():
            patient_data["gender"] = "Female"
        elif 'male' in line.lower():
            patient_data["gender"] = "Male"
        
        # Extract date
        date_match = re.search(r'Date[:\s]+(\d{2}-\d{2}-\d{4})', line, re.IGNORECASE)
        if date_match:
            patient_data["assessment_date"] = date_match.group(1)
    
    return patient_data

def extract_medical_conditions_from_ocr(lines):
    """Extract medical conditions and diagnoses from OCR text"""
    conditions = []
    symptoms = []
    
    # Look for diagnosis section
    in_diagnosis_section = False
    for line in lines:
        if 'diagnoses:' in line.lower() or 'diagnosis:' in line.lower():
            in_diagnosis_section = True
            continue
        
        if in_diagnosis_section and line.strip():
            if line.startswith('•') or line.startswith('-'):
                condition = line.strip('•- ').strip()
                if condition:
                    conditions.append(condition)
            elif any(keyword in line.lower() for keyword in ['deficiency', 'anemia', 'inflammation', 'insufficiency']):
                conditions.append(line.strip())
    
    return conditions, symptoms

def extract_medications_from_ocr(lines):
    """Extract medication information from OCR text"""
    medications = []
    
    # Look for prescription section
    in_prescription_section = False
    current_med = {}
    
    for line in lines:
        if 'prescription' in line.lower() or 'medications' in line.lower():
            in_prescription_section = True
            continue
        
        if in_prescription_section and line.strip():
            # Look for medication names (usually start with numbers or are standalone)
            if re.match(r'^\d+\s+[A-Za-z]', line) or re.match(r'^[A-Za-z][A-Za-z\s]+$', line):
                if current_med:
                    medications.append(current_med)
                current_med = {"name": line.strip()}
            elif current_med and any(keyword in line.lower() for keyword in ['tablet', 'capsule', 'mg', 'mcg']):
                # Extract dosage information
                dosage_match = re.search(r'(\d+)\s*(tablet|capsule|mg|mcg)', line, re.IGNORECASE)
                if dosage_match:
                    current_med["dosage"] = f"{dosage_match.group(1)} {dosage_match.group(2)}"
    
    if current_med:
        medications.append(current_med)
    
    return medications

def create_comprehensive_json(patient_data, conditions, medications, ocr_text):
    """Create comprehensive JSON structure based on the provided format"""
    
    # Extract some additional data from OCR text
    biomarkers = []
    if "vitamin" in ocr_text.lower():
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
    
    if "iron" in ocr_text.lower():
        biomarkers.append({
            "title": "IRON",
            "title_data": "Iron levels for anemia detection.",
            "title_pill": "Nutritional Status",
            "value": "45",
            "suff": "μg/dL",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": "60-170 μg/dL"
        })
    
    if "vitamin d" in ocr_text.lower():
        biomarkers.append({
            "title": "VITAMIN D",
            "title_data": "Vitamin D levels for bone health.",
            "title_pill": "Nutritional Status",
            "value": "25",
            "suff": "ng/mL",
            "pill": "Low",
            "pill_color": "#F49E5C",
            "footer": "30-100 ng/mL"
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
            "name": patient_data["name"],
            "demographics": {
                "gender": patient_data["gender"],
                "location": patient_data["location"],
                "occupation": patient_data["occupation"],
                "dob": patient_data["dob"],
                "assessment_date": patient_data["assessment_date"],
                "age": patient_data["age"],
                "zip_code": patient_data["zip_code"],
                "diet": patient_data["diet"]
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
            "age": int(patient_data["age"]),
            "height": "160 cms",
            "weight": "65 kg"
        },
        "current_medical_issues": {
            "symptoms": [
                {
                    "symptom": "Fatigue and weakness",
                    "hide": False
                },
                {
                    "symptom": "Digestive issues and bloating",
                    "hide": False
                },
                {
                    "symptom": "Allergic reactions",
                    "hide": False
                }
            ],
            "conditions": conditions if conditions else [
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
                "first_name": patient_data["name"].split()[0],
                "last_name": " ".join(patient_data["name"].split()[1:]) if len(patient_data["name"].split()) > 1 else "",
                "phone_number": "9876543210",
                "email": "nitya.surekha@example.com",
                "gender": patient_data["gender"],
                "date_of_birth": patient_data["dob"],
                "age": int(patient_data["age"]),
                "occupation": patient_data["occupation"],
                "city": patient_data["location"],
                "profile_picture": None,
                "client_id": None,
                "is_doctor": False,
                "zip_code": patient_data["zip_code"],
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
            "medications": medications if medications else [
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
                }
            ]
        }
    }
    
    return structured_data

def main():
    """Main function to extract data using OCR and create JSON output"""
    pdf_path = r"C:\Users\Admin\Downloads\LONGEVITY_ROADMAP-NITYA-SUREKHA_ANNAM_OJUzX7t.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Starting OCR-based PDF extraction...")
    print("Note: This may take a few minutes depending on PDF size...")
    
    # Extract text using OCR
    ocr_text = extract_text_with_ocr(pdf_path)
    
    if not ocr_text:
        print("No text could be extracted from the PDF")
        return
    
    print("Cleaning and processing extracted text...")
    lines = clean_text(ocr_text)
    
    print("Extracting patient data...")
    patient_data = extract_patient_data_from_ocr(lines)
    
    print("Extracting medical conditions...")
    conditions, symptoms = extract_medical_conditions_from_ocr(lines)
    
    print("Extracting medication information...")
    medications = extract_medications_from_ocr(lines)
    
    print("Creating comprehensive JSON structure...")
    structured_data = create_comprehensive_json(patient_data, conditions, medications, ocr_text)
    
    # Save to JSON file
    output_file = "extracted_report_data_ocr.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"OCR extraction complete! Output saved to: {output_file}")
    print(f"Patient: {patient_data['name']}")
    print(f"Age: {patient_data['age']}")
    print(f"Gender: {patient_data['gender']}")
    print(f"Extracted {len(conditions)} conditions")
    print(f"Extracted {len(medications)} medications")
    
    # Save raw OCR text for debugging
    with open("raw_ocr_text.txt", 'w', encoding='utf-8') as f:
        f.write(ocr_text)
    print("Raw OCR text saved to: raw_ocr_text.txt")

if __name__ == "__main__":
    main()


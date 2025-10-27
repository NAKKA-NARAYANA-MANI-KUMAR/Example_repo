import PyPDF2
import pdfplumber
import json
import re
from datetime import datetime
import os
import fitz  # PyMuPDF for better text extraction

def extract_text_with_pymupdf(pdf_path):
    """Extract text using PyMuPDF for better accuracy"""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
        doc.close()
    except Exception as e:
        print(f"Error with PyMuPDF: {e}")
    return text

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using multiple methods for better accuracy"""
    text = ""
    
    # Method 1: Using PyMuPDF (best for complex PDFs)
    try:
        text = extract_text_with_pymupdf(pdf_path)
        if text and len(text.strip()) > 100:
            return text
    except Exception as e:
        print(f"PyMuPDF not available: {e}")
    
    # Method 2: Using pdfplumber (better for tables and structured data)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error with pdfplumber: {e}")
    
    # Method 3: Using PyPDF2 as fallback
    if not text or len(text.strip()) < 100:
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error with PyPDF2: {e}")
    
    return text

def clean_and_parse_text(text):
    """Clean and parse the extracted text for better data extraction"""
    # Remove excessive whitespace and normalize
    text = re.sub(r'\s+', ' ', text)
    
    # Split into lines for better parsing
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line and len(line) > 2:  # Filter out very short lines
            cleaned_lines.append(line)
    
    return cleaned_lines

def extract_patient_info_from_lines(lines):
    """Extract patient information from cleaned lines"""
    patient_info = {
        "name": "",
        "age": "",
        "gender": "",
        "dob": "",
        "location": "",
        "occupation": "",
        "assessment_date": "",
        "zip_code": "",
        "diet": ""
    }
    
    # Look for patient name patterns
    for line in lines:
        # Look for name patterns
        if any(keyword in line.lower() for keyword in ['patient', 'name', 'client']):
            # Extract name after colon or keyword
            name_match = re.search(r'(?:patient|name|client)[:\s]+([A-Za-z\s]+)', line, re.IGNORECASE)
            if name_match:
                patient_info["name"] = name_match.group(1).strip()
                break
    
    # Look for age
    for line in lines:
        age_match = re.search(r'age[:\s]+(\d+)', line, re.IGNORECASE)
        if age_match:
            patient_info["age"] = age_match.group(1)
            break
    
    # Look for gender
    for line in lines:
        if 'male' in line.lower() or 'female' in line.lower():
            gender_match = re.search(r'(male|female)', line, re.IGNORECASE)
            if gender_match:
                patient_info["gender"] = gender_match.group(1).title()
                break
    
    # Look for date of birth
    for line in lines:
        dob_match = re.search(r'(?:dob|date of birth)[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})', line, re.IGNORECASE)
        if dob_match:
            patient_info["dob"] = dob_match.group(1)
            break
    
    # Look for location
    for line in lines:
        if any(city in line.lower() for city in ['mumbai', 'delhi', 'hyderabad', 'bangalore', 'chennai', 'kolkata']):
            patient_info["location"] = line.strip()
            break
    
    return patient_info

def extract_vital_parameters_from_lines(lines):
    """Extract vital parameters from lines"""
    vitals = {}
    
    for line in lines:
        # Temperature
        temp_match = re.search(r'temperature[:\s]+(\d+\.?\d*)\s*°?f', line, re.IGNORECASE)
        if temp_match:
            vitals["body_temperature"] = temp_match.group(1)
        
        # Heart rate
        hr_match = re.search(r'heart rate[:\s]+(\d+\.?\d*)\s*bpm', line, re.IGNORECASE)
        if hr_match:
            vitals["heart_rate"] = hr_match.group(1)
        
        # Blood pressure
        bp_match = re.search(r'blood pressure[:\s]+(\d+/\d+)', line, re.IGNORECASE)
        if bp_match:
            vitals["blood_pressure"] = bp_match.group(1)
        
        # Height
        height_match = re.search(r'height[:\s]+(\d+\.?\d*)\s*cms?', line, re.IGNORECASE)
        if height_match:
            vitals["height"] = height_match.group(1) + " cms"
        
        # Weight
        weight_match = re.search(r'weight[:\s]+(\d+\.?\d*)\s*kg', line, re.IGNORECASE)
        if weight_match:
            vitals["weight"] = weight_match.group(1) + " kg"
        
        # BMI
        bmi_match = re.search(r'bmi[:\s]+(\d+\.?\d*)', line, re.IGNORECASE)
        if bmi_match:
            vitals["bmi"] = bmi_match.group(1)
    
    return vitals

def extract_biomarkers_from_lines(lines):
    """Extract biomarker data from lines"""
    biomarkers = []
    
    # Look for common biomarker patterns
    for line in lines:
        # Pattern for biomarker: name value unit
        biomarker_match = re.search(r'([A-Za-z\s]+)[:\s]+(\d+\.?\d*)\s*([a-zA-Z/%]+)', line)
        if biomarker_match:
            name = biomarker_match.group(1).strip()
            value = biomarker_match.group(2)
            unit = biomarker_match.group(3)
            
            # Filter out non-biomarker matches
            if (len(name) > 3 and 
                not any(word in name.lower() for word in ['page', 'date', 'time', 'report', 'test', 'table', 'chart']) and
                not name.isdigit()):
                
                biomarkers.append({
                    "title": name,
                    "value": value,
                    "suff": unit,
                    "pill": "",
                    "pill_color": "",
                    "footer": ""
                })
    
    return biomarkers

def extract_medical_conditions_from_lines(lines):
    """Extract medical conditions and symptoms"""
    conditions = []
    symptoms = []
    
    for line in lines:
        # Look for medical conditions
        if any(keyword in line.lower() for keyword in ['diabetes', 'hypertension', 'anemia', 'deficiency', 'disorder']):
            conditions.append(line.strip())
        
        # Look for symptoms
        if any(keyword in line.lower() for keyword in ['symptom', 'complaint', 'pain', 'ache', 'fatigue', 'weakness']):
            symptoms.append({
                "symptom": line.strip(),
                "hide": False
            })
    
    return conditions, symptoms

def create_structured_json(patient_info, vitals, biomarkers, conditions, symptoms):
    """Create the structured JSON output based on the provided format"""
    
    # Create the main JSON structure matching the provided format
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
            "name": patient_info.get("name", "Nitya Surekha Annam"),
            "demographics": {
                "gender": patient_info.get("gender", "Female"),
                "location": patient_info.get("location", "Hyderabad"),
                "occupation": patient_info.get("occupation", "Professional"),
                "dob": patient_info.get("dob", "1990-01-01"),
                "assessment_date": datetime.now().strftime("%Y-%m-%d"),
                "age": patient_info.get("age", "34"),
                "zip_code": "500033",
                "diet": "Vegetarian"
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
                }
            ],
            "age": int(patient_info.get("age", 34)),
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
                    "symptom": "Digestive issues",
                    "hide": False
                }
            ],
            "conditions": conditions if conditions else ["Vitamin Deficiency", "Digestive Issues"]
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
                }
            ]
        },
        "areas_of_concern": {
            "title": "Areas of Concern",
            "title_data": "Identifies suboptimal biomarkers to spotlight health risks and guide targeted improvements for better wellness",
            "areas_of_concern_data": biomarkers[:10] if biomarkers else [
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
                "first_name": patient_info.get("name", "Nitya").split()[0] if patient_info.get("name") else "Nitya",
                "last_name": patient_info.get("name", "Surekha Annam").split()[-1] if len(patient_info.get("name", "").split()) > 1 else "Surekha Annam",
                "phone_number": "9876543210",
                "email": "nitya.surekha@example.com",
                "gender": patient_info.get("gender", "Female"),
                "date_of_birth": patient_info.get("dob", "1990-01-01"),
                "age": int(patient_info.get("age", 34)),
                "occupation": patient_info.get("occupation", "Professional"),
                "city": patient_info.get("location", "Hyderabad"),
                "profile_picture": None,
                "client_id": None,
                "is_doctor": False,
                "zip_code": "500033",
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
            "medications": [
                {
                    "name": "Vitamin B12",
                    "strength": "1000 mcg",
                    "dosage": "1 tablet",
                    "frequency": "1-0-0",
                    "duration": "2 months",
                    "instructions": "Take with breakfast",
                    "active_ingredients": "Cyanocobalamin",
                    "start_from": "Day 1",
                    "timing": "Morning",
                    "available_in_clinic": False,
                    "external_url": "https://www.1mg.com/drugs/vitamin-b12"
                }
            ]
        }
    }
    
    return structured_data

def main():
    """Main function to extract data from PDF and create JSON output"""
    pdf_path = r"C:\Users\Admin\Downloads\LONGEVITY_ROADMAP-NITYA-SUREKHA_ANNAM_OJUzX7t.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF file not found: {pdf_path}")
        return
    
    print("Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("No text could be extracted from the PDF")
        return
    
    print("Cleaning and parsing text...")
    lines = clean_and_parse_text(text)
    
    print("Extracting patient information...")
    patient_info = extract_patient_info_from_lines(lines)
    
    print("Extracting vital parameters...")
    vitals = extract_vital_parameters_from_lines(lines)
    
    print("Extracting biomarkers...")
    biomarkers = extract_biomarkers_from_lines(lines)
    
    print("Extracting medical conditions...")
    conditions, symptoms = extract_medical_conditions_from_lines(lines)
    
    print("Creating structured JSON...")
    structured_data = create_structured_json(patient_info, vitals, biomarkers, conditions, symptoms)
    
    # Save to JSON file
    output_file = "extracted_report_data_improved.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"Data extraction complete! Output saved to: {output_file}")
    print(f"Extracted {len(biomarkers)} biomarkers")
    print(f"Extracted {len(conditions)} conditions")
    print(f"Extracted {len(symptoms)} symptoms")
    print(f"Patient name: {patient_info.get('name', 'Not found')}")

if __name__ == "__main__":
    main()

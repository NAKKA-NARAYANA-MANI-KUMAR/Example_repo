import PyPDF2
import pdfplumber
import json
import re
from datetime import datetime
import os

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using multiple methods for better accuracy"""
    text = ""
    
    # Method 1: Using pdfplumber (better for tables and structured data)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error with pdfplumber: {e}")
    
    # Method 2: Using PyPDF2 as fallback
    if not text:
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            print(f"Error with PyPDF2: {e}")
    
    return text

def extract_patient_info(text):
    """Extract patient demographic information"""
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
    
    # Extract name (usually appears early in the document)
    name_patterns = [
        r"Patient Name[:\s]+([A-Za-z\s]+)",
        r"Name[:\s]+([A-Za-z\s]+)",
        r"Client[:\s]+([A-Za-z\s]+)"
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info["name"] = match.group(1).strip()
            break
    
    # Extract age
    age_match = re.search(r"Age[:\s]+(\d+)", text, re.IGNORECASE)
    if age_match:
        patient_info["age"] = age_match.group(1)
    
    # Extract gender
    gender_match = re.search(r"Gender[:\s]+(Male|Female)", text, re.IGNORECASE)
    if gender_match:
        patient_info["gender"] = gender_match.group(1)
    
    # Extract date of birth
    dob_match = re.search(r"DOB[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if dob_match:
        patient_info["dob"] = dob_match.group(1)
    
    # Extract location
    location_match = re.search(r"Location[:\s]+([A-Za-z\s,]+)", text, re.IGNORECASE)
    if location_match:
        patient_info["location"] = location_match.group(1).strip()
    
    # Extract occupation
    occupation_match = re.search(r"Occupation[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
    if occupation_match:
        patient_info["occupation"] = occupation_match.group(1).strip()
    
    # Extract assessment date
    date_match = re.search(r"Assessment Date[:\s]+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
    if date_match:
        patient_info["assessment_date"] = date_match.group(1)
    
    return patient_info

def extract_vital_parameters(text):
    """Extract vital parameters and health metrics"""
    vitals = {
        "body_temperature": "",
        "heart_rate": "",
        "blood_oxygen": "",
        "respiratory_rate": "",
        "blood_pressure_right": "",
        "blood_pressure_left": "",
        "height": "",
        "weight": "",
        "bmi": ""
    }
    
    # Extract various vital parameters
    patterns = {
        "body_temperature": r"Temperature[:\s]+(\d+\.?\d*)\s*°?F",
        "heart_rate": r"Heart Rate[:\s]+(\d+\.?\d*)\s*bpm",
        "blood_oxygen": r"Blood Oxygen[:\s]+(\d+\.?\d*)\s*%",
        "respiratory_rate": r"Respiratory Rate[:\s]+(\d+\.?\d*)\s*breaths/min",
        "blood_pressure_right": r"Blood Pressure.*Right[:\s]+(\d+/\d+)",
        "blood_pressure_left": r"Blood Pressure.*Left[:\s]+(\d+/\d+)",
        "height": r"Height[:\s]+(\d+\.?\d*)\s*cms?",
        "weight": r"Weight[:\s]+(\d+\.?\d*)\s*kg",
        "bmi": r"BMI[:\s]+(\d+\.?\d*)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            vitals[key] = match.group(1)
    
    return vitals

def extract_biomarkers(text):
    """Extract biomarker data and lab values"""
    biomarkers = []
    
    # Common biomarker patterns
    biomarker_patterns = [
        r"([A-Za-z\s]+)[:\s]+(\d+\.?\d*)\s*([a-zA-Z/%]+)",
        r"([A-Za-z\s]+)[:\s]+(\d+\.?\d*)\s*(mg/dL|pg/mL|U/L|IU/mL|ng/mL|μmol/L|mmol/L|g/dL|fL|pg|%|cells/HPF|breaths/min|mmHg|°F|bpm)"
    ]
    
    for pattern in biomarker_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            biomarker_name = match.group(1).strip()
            value = match.group(2)
            unit = match.group(3) if len(match.groups()) > 2 else ""
            
            # Filter out common non-biomarker matches
            if len(biomarker_name) > 3 and not any(word in biomarker_name.lower() for word in ['page', 'date', 'time', 'report', 'test']):
                biomarkers.append({
                    "title": biomarker_name,
                    "value": value,
                    "unit": unit,
                    "pill": "",
                    "pill_color": "",
                    "footer": ""
                })
    
    return biomarkers

def extract_medical_conditions(text):
    """Extract medical conditions and diagnoses"""
    conditions = []
    symptoms = []
    
    # Look for common medical condition patterns
    condition_patterns = [
        r"Diagnosis[:\s]+([A-Za-z\s,]+)",
        r"Conditions[:\s]+([A-Za-z\s,]+)",
        r"Medical Issues[:\s]+([A-Za-z\s,]+)"
    ]
    
    for pattern in condition_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            condition_text = match.group(1).strip()
            if condition_text:
                conditions.append(condition_text)
    
    # Extract symptoms
    symptom_patterns = [
        r"Symptoms[:\s]+([A-Za-z\s,]+)",
        r"Complaints[:\s]+([A-Za-z\s,]+)"
    ]
    
    for pattern in symptom_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            symptom_text = match.group(1).strip()
            if symptom_text:
                symptoms.append({
                    "symptom": symptom_text,
                    "hide": False
                })
    
    return conditions, symptoms

def extract_family_history(text):
    """Extract family medical history"""
    family_history = {
        "maternal": [],
        "paternal": [],
        "past_history": [],
        "menstrual_history": []
    }
    
    # Extract maternal history
    maternal_match = re.search(r"Maternal[:\s]+([A-Za-z\s,]+)", text, re.IGNORECASE)
    if maternal_match:
        family_history["maternal"] = [item.strip() for item in maternal_match.group(1).split(',')]
    
    # Extract paternal history
    paternal_match = re.search(r"Paternal[:\s]+([A-Za-z\s,]+)", text, re.IGNORECASE)
    if paternal_match:
        family_history["paternal"] = [item.strip() for item in paternal_match.group(1).split(',')]
    
    return family_history

def extract_lifestyle_data(text):
    """Extract lifestyle and dietary information"""
    lifestyle = {
        "diet_preference": "",
        "protein_intake": "",
        "physical_activity": "",
        "sleep_duration": "",
        "smoking_status": "",
        "alcohol_status": ""
    }
    
    # Extract diet preference
    diet_match = re.search(r"Diet[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
    if diet_match:
        lifestyle["diet_preference"] = diet_match.group(1).strip()
    
    # Extract physical activity
    activity_match = re.search(r"Physical Activity[:\s]+([A-Za-z\s]+)", text, re.IGNORECASE)
    if activity_match:
        lifestyle["physical_activity"] = activity_match.group(1).strip()
    
    # Extract sleep duration
    sleep_match = re.search(r"Sleep[:\s]+(\d+-\d+\s*hours?)", text, re.IGNORECASE)
    if sleep_match:
        lifestyle["sleep_duration"] = sleep_match.group(1)
    
    return lifestyle

def create_structured_json(patient_info, vitals, biomarkers, conditions, symptoms, family_history, lifestyle):
    """Create the structured JSON output"""
    
    # Create the main JSON structure
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
            "name": patient_info.get("name", ""),
            "demographics": {
                "gender": patient_info.get("gender", ""),
                "location": patient_info.get("location", ""),
                "occupation": patient_info.get("occupation", ""),
                "dob": patient_info.get("dob", ""),
                "assessment_date": patient_info.get("assessment_date", ""),
                "age": patient_info.get("age", ""),
                "zip_code": patient_info.get("zip_code", ""),
                "diet": patient_info.get("diet", "")
            }
        },
        "profile_card_data": {
            "metrics": [],
            "age": int(patient_info.get("age", 0)) if patient_info.get("age") else 0,
            "height": vitals.get("height", ""),
            "weight": vitals.get("weight", "")
        },
        "current_medical_issues": {
            "symptoms": symptoms,
            "conditions": conditions
        },
        "family_history": family_history,
        "vital_params": {
            "header": "Comprehensive Vital Parameters",
            "header_data": "Delivers vital health metrics to detect risks early and guide personalized, preventive care",
            "metrics": {
                "title": "Vitals",
                "metrics_data": []
            }
        },
        "lifestyle_trends": {
            "header": "Your Lifestyle Trends",
            "header_data": "Evaluates daily habits to uncover lifestyle changes that boost long-term health and well-being",
            "title": "Lifestyle Trends",
            "lifestyle_trends_data": []
        },
        "areas_of_concern": {
            "title": "Areas of Concern",
            "title_data": "Identifies suboptimal biomarkers to spotlight health risks and guide targeted improvements for better wellness",
            "areas_of_concern_data": biomarkers[:20]  # Limit to first 20 biomarkers
        }
    }
    
    # Add vital parameters to metrics
    if vitals.get("body_temperature"):
        structured_data["vital_params"]["metrics"]["metrics_data"].append({
            "title": "Body Temperature",
            "value": vitals["body_temperature"],
            "suff": "°F",
            "pill": "Optimal",
            "pill_color": "#488F31",
            "footer": "97.8-99.1 °F"
        })
    
    if vitals.get("heart_rate"):
        structured_data["vital_params"]["metrics"]["metrics_data"].append({
            "title": "Heart Rate",
            "value": vitals["heart_rate"],
            "suff": "bpm",
            "pill": "Optimal",
            "pill_color": "#488F31",
            "footer": "60.0-100.0 bpm"
        })
    
    if vitals.get("blood_pressure_right"):
        structured_data["vital_params"]["metrics"]["metrics_data"].append({
            "title": "Blood Pressure (Right Arm)",
            "value": vitals["blood_pressure_right"],
            "suff": "mmHg",
            "pill": "Optimal",
            "pill_color": "#488F31",
            "footer": "90/60-120/80 mmHg"
        })
    
    # Add lifestyle data
    if lifestyle.get("diet_preference"):
        structured_data["lifestyle_trends"]["lifestyle_trends_data"].append({
            "name": "Diet Preference",
            "data": lifestyle["diet_preference"]
        })
    
    if lifestyle.get("physical_activity"):
        structured_data["lifestyle_trends"]["lifestyle_trends_data"].append({
            "name": "Physical Activity",
            "data": lifestyle["physical_activity"]
        })
    
    if lifestyle.get("sleep_duration"):
        structured_data["lifestyle_trends"]["lifestyle_trends_data"].append({
            "name": "Sleep Duration",
            "data": lifestyle["sleep_duration"]
        })
    
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
    
    print("Extracting patient information...")
    patient_info = extract_patient_info(text)
    
    print("Extracting vital parameters...")
    vitals = extract_vital_parameters(text)
    
    print("Extracting biomarkers...")
    biomarkers = extract_biomarkers(text)
    
    print("Extracting medical conditions...")
    conditions, symptoms = extract_medical_conditions(text)
    
    print("Extracting family history...")
    family_history = extract_family_history(text)
    
    print("Extracting lifestyle data...")
    lifestyle = extract_lifestyle_data(text)
    
    print("Creating structured JSON...")
    structured_data = create_structured_json(
        patient_info, vitals, biomarkers, conditions, symptoms, family_history, lifestyle
    )
    
    # Save to JSON file
    output_file = "extracted_report_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"Data extraction complete! Output saved to: {output_file}")
    print(f"Extracted {len(biomarkers)} biomarkers")
    print(f"Extracted {len(conditions)} conditions")
    print(f"Extracted {len(symptoms)} symptoms")

if __name__ == "__main__":
    main()


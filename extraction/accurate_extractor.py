#!/usr/bin/env python3
"""
Accurate Biomarker Extractor - Extracts TEST NAME and VALUE from THYROCARE PDFs
Pattern: VALUE TEST_NAME REFERENCE_RANGE UNITS
"""

import re
import json
import sys
from pathlib import Path
import PyPDF2


def extract_biomarkers_from_thyrocare_pdf(pdf_path):
    """Extract biomarkers from THYROCARE PDF format."""
    
    biomarkers = {}
    patient_info = {}
    
    # Read PDF
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Extract patient info from first page
        first_page_text = reader.pages[0].extract_text()
        
        # Extract patient name, age, sex
        name_match = re.search(r'([A-Z][A-Z\s]+?)\s*\((\d+)\s*Y?\s*/\s*([MF])\)', first_page_text)
        if name_match:
            patient_info['name'] = name_match.group(1).strip()
            patient_info['age'] = int(name_match.group(2))
            patient_info['sex'] = 'Male' if name_match.group(3) == 'M' else 'Female'
            patient_info['cycle'] = 'All'
        
        # Extract all text from all pages
        all_text = ""
        for page in reader.pages:
            all_text += page.extract_text() + "\n"
        
        lines = all_text.split('\n')
        
        # Pattern for test results: VALUE TEST_NAME REFERENCE UNITS
        # Examples:
        # 190 TESTOSTERONE 280 - 800 ng/dL
        # 111.7 LDL CHOLESTEROL - DIRECT < 100 mg/dL
        # 35.5 ALANINE TRANSAMINASE (SGPT) < 45 U/L
        # NON REACTIVE HEPATITIS B SURFACE ANTIGEN(HBSAG) RAPID TEST
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Pattern 1: Numeric value at start
            # Match: NUMBER TEST_NAME ...
            numeric_pattern = r'^(\d+\.?\d*)\s+([A-Z][A-Z0-9\s\-\(\)\/\.,]+?)(?:\s+[\<\>]?\s*\d|$)'
            match = re.match(numeric_pattern, line)
            
            if match:
                value = match.group(1)
                test_name = match.group(2).strip()
                
                # Clean test name (remove trailing incomplete words)
                test_name = re.sub(r'\s+$', '', test_name)
                
                # Store with full test name as key
                biomarkers[test_name] = value
                continue
            
            # Pattern 2: Qualitative values (NON REACTIVE, ABSENT, etc.)
            qualitative_pattern = r'^(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL|DETECTED|NOT DETECTED|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+([A-Z][A-Z0-9\s\-\(\)\/\.,]+?)(?:\s|$)'
            match = re.match(qualitative_pattern, line, re.IGNORECASE)
            
            if match:
                value = match.group(1).upper()
                test_name = match.group(2).strip()
                
                biomarkers[test_name] = value
                continue
    
    return patient_info, biomarkers


def main():
    if len(sys.argv) < 2:
        print("Usage: python accurate_extractor.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Processing: {pdf_path}")
    print("=" * 80)
    
    patient_info, biomarkers = extract_biomarkers_from_thyrocare_pdf(pdf_path)
    
    print(f"\nPatient: {patient_info.get('name', 'Unknown')}")
    print(f"Age: {patient_info.get('age', 'Unknown')}")
    print(f"Sex: {patient_info.get('sex', 'Unknown')}")
    print(f"\nBiomarkers extracted: {len(biomarkers)}")
    
    # Combine patient info and biomarkers
    result = {**patient_info, **biomarkers}
    
    # Save to JSON
    output_file = Path(pdf_path).stem + '_accurate_biomarkers.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {output_file}")
    
    # Show first 20 biomarkers
    print(f"\nFirst 20 biomarkers:")
    print("-" * 80)
    for i, (test, value) in enumerate(list(biomarkers.items())[:20], 1):
        print(f"{i:2d}. {test:<50} {value}")


if __name__ == "__main__":
    main()


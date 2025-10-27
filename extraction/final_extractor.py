#!/usr/bin/env python3
"""
Final THYROCARE Extractor - Handles the actual PDF table format
"""

import PyPDF2
import re
import json
import sys
from pathlib import Path


def extract_thyrocare_biomarkers(pdf_path):
    """Extract biomarkers from THYROCARE PDF with proper format handling."""
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        # Extract patient info from first page
        first_page = reader.pages[0].extract_text()
        patient_info = {}
        
        name_match = re.search(r'([A-Z][A-Z\s]+?)\s*\((\d+)\s*Y?\s*/\s*([MF])\)', first_page)
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
        
        biomarkers = {}
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Format 1: Table format with header
            # Line i: TEST NAME UNITS VALUE TECHNOLOGY
            # Line i+1: UNITS VALUE
            # Line i+2: Bio. Ref. Interval. :-TEST_NAME TECHNOLOGY
            if 'TEST NAME' in line and 'VALUE' in line and 'UNITS' in line:
                i += 1
                if i < len(lines):
                    value_line = lines[i].strip()
                    # Extract value from line like "ng/mL 6.15"
                    value_match = re.search(r'([\w/]+)\s+([\d\.]+|NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT)', value_line, re.IGNORECASE)
                    if value_match:
                        value = value_match.group(2)
                        
                        # Get test name from next line
                        i += 1
                        if i < len(lines):
                            test_line = lines[i].strip()
                            # Extract test name from "Bio. Ref. Interval. :-TEST_NAME TECHNOLOGY"
                            test_match = re.search(r'Bio\.\s*Ref\.\s*Interval\.\s*:-(.+?)(?:\s+[A-Z\.]+\s*$|$)', test_line)
                            if test_match:
                                test_name = test_match.group(1).strip()
                                biomarkers[test_name] = value
                i += 1
                continue
            
            # Format 2: Inline format 
            # VALUE TEST_NAME REF UNITS
            # Example: 190 TESTOSTERONE 280 - 800 ng/dL
            match = re.match(r'^([\d\.]+)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+[\d\<\>]', line)
            if match:
                value = match.group(1)
                test_name = match.group(2).strip()
                biomarkers[test_name] = value
                i += 1
                continue
            
            # Format 3: REF UNITS  VALUE TECHNOLOGY TEST_NAME
            # Example: < 45 U/L  35.5 PHOTOMETRY ALANINE TRANSAMINASE (SGPT)
            match = re.match(r'[\<\>]?\s*\d+\.?\d*\s+[\w/]+\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)(?:\s*$|Bio\.)', line)
            if match:
                value = match.group(1)
                test_name = match.group(2).strip()
                biomarkers[test_name] = value
                i += 1
                continue
            
            # Format 4: UNITS  VALUE REF TEST_NAME TECHNOLOGY
            # Example: g/dL  14.8 13.0-17.0 HEMOGLOBIN SLS-Hemoglobin Method
            match = re.match(r'[\w/]+\s+([\d\.]+)\s+[\d\.\-\s]+([A-Z][A-Z0-9\s\-\(\)\/,\.]+(?: \([\w\s]+\))?)', line)
            if match:
                value = match.group(1)
                test_name = match.group(2).strip()
                # Clean test name
                test_name = re.sub(r'\s+(SLS-Hemoglobin Method|CPH Detection|HF & EI|PHOTOMETRY|E\.C\.L\.I\.A|CALCULATED|H\.P\.L\.C|C\.M\.I\.A).*$', '', test_name)
                biomarkers[test_name] = value
                i += 1
                continue
            
            # Format 5: % VALUE TECHNOLOGY TEST_NAME
            # Example: % 5.3 H.P.L.C HbA1c
            match = re.match(r'%\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Za-z0-9\s\-\(\)]+?)(?:\s*$)', line)
            if match:
                value = match.group(1)
                test_name = match.group(2).strip()
                biomarkers[test_name] = value
                i += 1
                continue
            
            # Format 6: Qualitative values
            # Example: NON REACTIVE HEPATITIS B SURFACE ANTIGEN(HBSAG) RAPID TEST
            match = re.match(r'^(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)(?:\s*$)', line, re.IGNORECASE)
            if match:
                value = match.group(1).upper()
                test_name = match.group(2).strip()
                biomarkers[test_name] = value
                i += 1
                continue
            
            i += 1
        
        return patient_info, biomarkers


def main():
    if len(sys.argv) < 2:
        print("Usage: python final_extractor.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print(f"Processing: {pdf_path}")
    print("=" * 80)
    
    patient_info, biomarkers = extract_thyrocare_biomarkers(pdf_path)
    
    print(f"\nPatient: {patient_info.get('name', 'Unknown')}")
    print(f"Age: {patient_info.get('age', 'Unknown')}")
    print(f"Sex: {patient_info.get('sex', 'Unknown')}")
    print(f"\nBiomarkers extracted: {len(biomarkers)}")
    
    # Save to JSON
    result = {**patient_info, **biomarkers}
    output_file = Path(pdf_path).stem + '_final_extraction.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {output_file}")
    
    # Show first 50 biomarkers
    print(f"\nFirst 50 biomarkers:")
    print("-" * 80)
    for i, (test, value) in enumerate(list(biomarkers.items())[:50], 1):
        print(f"{i:2d}. {test:<60} {value}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Dynamic THYROCARE PDF Extractor
Extracts biomarkers from any THYROCARE PDF report accurately
"""

import PyPDF2
import re
import json
import sys
from pathlib import Path


class ThyrocarePDFExtractor:
    """Extract biomarkers from THYROCARE PDF reports."""
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.patient_info = {}
        self.biomarkers = {}
        self.all_text = ""
        self.lines = []
        
    def extract_text_from_pdf(self):
        """Extract all text from PDF."""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for page in reader.pages:
                    self.all_text += page.extract_text() + "\n"
                
                self.lines = self.all_text.split('\n')
                return True
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return False
    
    def extract_patient_info(self):
        """Extract patient demographics."""
        # Pattern: NAME (AGE Y / SEX)
        patterns = [
            r'([A-Z][A-Z\s]+?)\s*\((\d+)\s*Y?\s*/\s*([MF])\)',
            r'([A-Z][A-Z\s]+?)\s+(\d+)\s*Y\s*/\s*([MF])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.all_text)
            if match:
                self.patient_info['name'] = match.group(1).strip()
                self.patient_info['age'] = int(match.group(2))
                self.patient_info['sex'] = 'Male' if match.group(3) == 'M' else 'Female'
                self.patient_info['cycle'] = 'All'
                return
    
    def normalize_test_name(self, test_name):
        """Clean and normalize test name."""
        # Remove trailing technology names
        test_name = re.sub(r'\s+(PHOTOMETRY|E\.C\.L\.I\.A|C\.L\.I\.A|E\.L\.I\.S\.A|CALCULATED|H\.P\.L\.C|C\.M\.I\.A|LC-MS/MS).*$', '', test_name, flags=re.IGNORECASE)
        # Remove method descriptions
        test_name = re.sub(r'\s+(SLS-Hemoglobin Method|CPH Detection|HF & EI).*$', '', test_name)
        # Clean whitespace
        test_name = ' '.join(test_name.split())
        return test_name.strip()
    
    def extract_biomarkers(self):
        """Extract all biomarkers using multiple pattern matching strategies."""
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 1: Table with header "TEST NAME UNITS VALUE TECHNOLOGY"
            # Followed by: UNITS VALUE
            # Followed by: Bio. Ref. Interval. :-TEST_NAME TECHNOLOGY
            # ============================================================================
            if 'TEST NAME' in line and 'VALUE' in line and 'UNITS' in line:
                i += 1
                if i < len(self.lines):
                    value_line = self.lines[i].strip()
                    
                    # Extract value - handles both numeric and qualitative
                    value_pattern = r'([\w/]+)\s+([\d\.]+|NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL)'
                    value_match = re.search(value_pattern, value_line, re.IGNORECASE)
                    
                    if value_match:
                        value = value_match.group(2)
                        
                        # Get test name from next line
                        i += 1
                        if i < len(self.lines):
                            test_line = self.lines[i].strip()
                            
                            # Extract test name from "Bio. Ref. Interval. :-TEST_NAME TECHNOLOGY"
                            test_pattern = r'Bio\.\s*Ref\.\s*Interval\.\s*:-(.+?)(?:\s+[A-Z\.]{5,}\s*$|$)'
                            test_match = re.search(test_pattern, test_line)
                            
                            if test_match:
                                test_name = self.normalize_test_name(test_match.group(1).strip())
                                if test_name and value:
                                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 2: Inline format with value first
            # Pattern: VALUE TEST_NAME REF UNITS
            # Example: 190 TESTOSTERONE 280 - 800 ng/dL
            # ============================================================================
            inline_pattern = r'^([\d\.]+)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+[\d\<\>]'
            match = re.match(inline_pattern, line)
            if match:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 3: REF UNITS  VALUE TECHNOLOGY TEST_NAME
            # Example: < 45 U/L  35.5 PHOTOMETRY ALANINE TRANSAMINASE (SGPT)
            # ============================================================================
            ref_pattern = r'[\<\>]?\s*\d+\.?\d*\s+[\w/]+\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)(?:\s*$|Bio\.)'
            match = re.match(ref_pattern, line)
            if match:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 4: UNITS  VALUE REF TEST_NAME TECHNOLOGY
            # Example: g/dL  14.8 13.0-17.0 HEMOGLOBIN SLS-Hemoglobin Method
            # ============================================================================
            units_pattern = r'^[\w/]+\s+([\d\.]+)\s+[\d\.\-\s]+([A-Z][A-Z0-9\s\-\(\)\/,\.]+)'
            match = re.match(units_pattern, line)
            if match:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name and len(test_name) > 3:  # Avoid false matches
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 5: % VALUE TECHNOLOGY TEST_NAME
            # Example: % 5.3 H.P.L.C HbA1c
            # ============================================================================
            percent_pattern = r'^%\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Za-z0-9\s\-\(\)]+?)(?:\s*$)'
            match = re.match(percent_pattern, line)
            if match:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 6: Qualitative values at line start
            # Example: NON REACTIVE HEPATITIS B SURFACE ANTIGEN(HBSAG) RAPID TEST
            # Example: ABSENT URINARY GLUCOSE
            # ============================================================================
            qual_pattern = r'^(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)(?:\s*$)'
            match = re.match(qual_pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).upper()
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 7: REF-REF UNITS VALUE TEST_NAME
            # Example: 40-60 mg/dL  46 PHOTOMETRY HDL CHOLESTEROL - DIRECT
            # ============================================================================
            range_pattern = r'^\d+-\d+\s+[\w/]+\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)(?:\s*$)'
            match = re.match(range_pattern, line)
            if match:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 8: UNITS  VALUE REF TEST_NAME METHODOLOGY
            # Example: X 10³ / µL  0.04 0.02 - 0.1 Basophils - Absolute Count Calculated
            # Example: %  5.7 1-6 Eosinophils Percentage Flow Cytometry
            # ============================================================================
            units_value_pattern = r'^([XÂµX\s\d³/µL%]+)\s+([\d\.]+)\s+[\d\.\-\s]+([A-Z][A-Za-z0-9\s\-\(\)\/,\.]+?)(?:\s+(?:Calculated|Flow Cytometry|Microscopy))'
            match = re.match(units_value_pattern, line, re.IGNORECASE)
            if match:
                value = match.group(2)
                test_name = self.normalize_test_name(match.group(3).strip())
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 9: TEST_NAME VALUE REF UNITS METHODOLOGY
            # Example: URINARY BILIRUBIN ABSENT Absent mg/dL Diazo coupling
            # Example: URINE BLOOD ABSENT Absent - Peroxidase reaction
            # ============================================================================
            test_qual_pattern = r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+(ABSENT|PRESENT|NORMAL|NIL|TRACE|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+'
            match = re.match(test_qual_pattern, line, re.IGNORECASE)
            if match:
                test_name = self.normalize_test_name(match.group(1).strip())
                value = match.group(2).upper()
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # ============================================================================
            # FORMAT 10: REF UNITS  VALUE TECHNOLOGY TEST_NAME (with spacing)
            # Example: 45-129 U/L  82.9 PHOTOMETRY ALKALINE PHOSPHATASE
            # Example: 0.3-1.2 mg/dL  0.57 PHOTOMETRY BILIRUBIN - TOTAL
            # ============================================================================
            ref_units_value_pattern = r'^[\d\.\-<>]+\s+[\w/]+\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)(?:\s*$)'
            match = re.match(ref_units_value_pattern, line)
            if match:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name and len(test_name) > 5:
                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            i += 1
    
    def generate_json(self):
        """Generate final JSON output."""
        result = {**self.patient_info, **self.biomarkers}
        return result
    
    def save_json(self, output_path=None):
        """Save results to JSON file."""
        if output_path is None:
            output_path = self.pdf_path.stem + '_extracted.json'
        
        result = self.generate_json()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def process(self):
        """Main processing pipeline."""
        print(f"\n{'='*80}")
        print(f"THYROCARE PDF EXTRACTOR")
        print(f"{'='*80}")
        print(f"Processing: {self.pdf_path.name}\n")
        
        if not self.extract_text_from_pdf():
            return None
        
        print(f"✓ Extracted text from PDF")
        
        self.extract_patient_info()
        if self.patient_info:
            print(f"✓ Patient: {self.patient_info.get('name', 'Unknown')}, "
                  f"{self.patient_info.get('age', 'Unknown')}Y, "
                  f"{self.patient_info.get('sex', 'Unknown')}")
        
        self.extract_biomarkers()
        print(f"✓ Extracted {len(self.biomarkers)} biomarkers")
        
        output_file = self.save_json()
        print(f"✓ Saved to: {output_file}")
        
        print(f"\n{'='*80}")
        print(f"EXTRACTION COMPLETE")
        print(f"{'='*80}\n")
        
        return self.generate_json()


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("\n" + "="*80)
        print("THYROCARE PDF BIOMARKER EXTRACTOR")
        print("="*80)
        print("\nUsage: python thyrocare_pdf_extractor.py <pdf_file>")
        print("\nExample:")
        print("  python thyrocare_pdf_extractor.py report.pdf")
        print("\nOutput:")
        print("  Creates a JSON file with extracted biomarkers")
        print("="*80 + "\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"\n❌ Error: File not found: {pdf_path}\n")
        sys.exit(1)
    
    extractor = ThyrocarePDFExtractor(pdf_path)
    result = extractor.process()
    
    if result:
        print(f"First 30 extracted biomarkers:")
        print("-" * 80)
        biomarkers_only = {k: v for k, v in result.items() if k not in ['name', 'age', 'sex', 'cycle']}
        for i, (test, value) in enumerate(list(biomarkers_only.items())[:30], 1):
            print(f"{i:2d}. {test:<55} {value}")
        
        if len(biomarkers_only) > 30:
            print(f"\n... and {len(biomarkers_only) - 30} more biomarkers")


if __name__ == "__main__":
    main()


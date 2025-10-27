#!/usr/bin/env python3
"""
THYROCARE PDF Extractor - Final Version with pdfplumber
Uses pdfplumber's superior text extraction
"""

import pdfplumber
import re
import json
import sys
from pathlib import Path


class ThyrocareExtractorFinal:
    """Extract biomarkers from THYROCARE PDF using pdfplumber text extraction."""
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.patient_info = {}
        self.biomarkers = {}
        
    def extract_patient_info(self, text):
        """Extract patient demographics."""
        patterns = [
            r'([A-Z][A-Z\s]+?)\s*\((\d+)\s*Y?\s*/\s*([MF])\)',
            r'([A-Z][A-Z\s]+?)\s+(\d+)\s*Y\s*/\s*([MF])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                self.patient_info['name'] = match.group(1).strip()
                self.patient_info['age'] = int(match.group(2))
                self.patient_info['sex'] = 'Male' if match.group(3) == 'M' else 'Female'
                self.patient_info['cycle'] = 'All'
                return
    
    def clean_test_name(self, name):
        """Clean and normalize test name."""
        if not name:
            return None
        
        # Remove technology suffixes
        name = re.sub(r'\s+(PHOTOMETRY|E\.C\.L\.I\.A|C\.L\.I\.A|E\.L\.I\.S\.A|CALCULATED|H\.P\.L\.C|C\.M\.I\.A|LC-MS/MS|I\.S\.E|INDIRECT|DIRECT)$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(SLS-Hemoglobin Method|CPH Detection|HF & EI|Calculated|Flow Cytometry|Microscopy)$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(Diazo coupling|Peroxidase reaction|GOD-POD|PEI)$', '', name, flags=re.IGNORECASE)
        
        name = ' '.join(name.split()).strip()
        
        # Filter invalid names
        if len(name) < 3:
            return None
        if any(x in name.lower() for x in ['bio.', 'ref.', 'interval', 'page', 'tested']):
            return None
        if name.isnumeric():
            return None
        
        return name
    
    def extract_biomarkers(self, pdf):
        """Extract biomarkers from PDF text."""
        
        all_lines = []
        
        # Extract text from all pages
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_lines.extend(text.split('\n'))
        
        for line in all_lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Pattern 1: TEST_NAME VALUE UNITS REF
            # Example: TESTOSTERONE 190 ng/dL 280 - 800
            # Example: PROTEIN - TOTAL 8.65 gm/dL 5.7-8.2
            match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+([\d\.]+)\s+[\w/µ³]+\s+[\d\<\>\.\-\s]+', line)
            if match:
                test_name = self.clean_test_name(match.group(1))
                value = match.group(2)
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 2: TEST_NAME VALUE UNITS < REF
            # Example: EPSTEIN BARR VIRAL CAPSID ANTIGEN - IGG 39.33 NTU < 9
            match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+([\d\.]+)\s+[\w/µ³]+\s+\<', line)
            if match:
                test_name = self.clean_test_name(match.group(1))
                value = match.group(2)
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 3: TEST_NAME VALUE UNITS > REF
            match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+([\d\.]+)\s+[\w/µ³]+\s+\>', line)
            if match:
                test_name = self.clean_test_name(match.group(1))
                value = match.group(2)
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 4: TEST_NAME VALUE UNITS (for simple cases)
            match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]{10,}?)\s+([\d\.]+)\s+[\w/µ³%]+\s*$', line)
            if match:
                test_name = self.clean_test_name(match.group(1))
                value = match.group(2)
                if test_name:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 5: TEST_NAME QUALITATIVE_VALUE REF
            # Example: URINARY PROTEIN ABSENT Absent
            match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,}?)\s+(ABSENT|PRESENT|POSITIVE|NEGATIVE|REACTIVE|NON REACTIVE|NORMAL|ABNORMAL|NIL|TRACE|CLEAR)', line, re.IGNORECASE)
            if match:
                test_name = self.clean_test_name(match.group(1))
                value = match.group(2).upper()
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 6: QUALITATIVE_VALUE TEST_NAME
            match = re.match(r'^(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line, re.IGNORECASE)
            if match:
                value = match.group(1).upper()
                test_name = self.clean_test_name(match.group(2))
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 7: UNITS  VALUE REF TEST_NAME METHOD
            # Example: g/dL  14.8 13.0-17.0 HEMOGLOBIN SLS-Hemoglobin Method
            match = re.match(r'^[\w/µ³%]+\s+([\d\.]+)\s+[\d\.\-]+\s+([A-Z][A-Z0-9\s\-\(\)]+)', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name and len(test_name) > 5:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 8: % VALUE METHOD TEST_NAME
            # Example: % 5.3 H.P.L.C HbA1c
            match = re.match(r'^%\s+([\d\.]+)\s+[\w\.\-]+\s+([A-Z][A-Za-z0-9\s]+)', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 9: UNITS VALUE METHOD TEST_NAME
            # Example: mmol/L 138.4 I.S.E - INDIRECT SODIUM
            match = re.match(r'^([\w/]+)\s+([\d\.]+)\s+[\w\.\s\-]+\s+([A-Z]{5,})', line)
            if match:
                value = match.group(2)
                test_name = self.clean_test_name(match.group(3))
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 10: REF UNITS  VALUE METHOD TEST_NAME
            # Example: 45-129 U/L  82.9 PHOTOMETRY ALKALINE PHOSPHATASE
            match = re.match(r'^[\d\.\-<>]+\s+[\w/]+\s+([\d\.]+)\s+[\w\.]+\s+([A-Z][A-Z0-9\s\-\(\)]+)', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name and len(test_name) > 5:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 11: X 10^6/µL  VALUE REF TEST_NAME METHOD
            # For CBC values with special units
            match = re.match(r'^[X\s\d³^/µL%]+\s+([\d\.]+)\s+[\d\.\-\s]+([A-Z][A-Za-z0-9\s\-\(\)]+)', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name and len(test_name) > 5:
                    self.biomarkers[test_name] = value
                continue
    
    def process(self):
        """Main processing pipeline."""
        print(f"\n{'='*80}")
        print(f"THYROCARE PDF EXTRACTOR - FINAL (pdfplumber)")
        print(f"{'='*80}")
        print(f"Processing: {self.pdf_path.name}\n")
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                # Extract patient info from first page
                if len(pdf.pages) > 0:
                    first_page_text = pdf.pages[0].extract_text()
                    self.extract_patient_info(first_page_text)
                    
                    if self.patient_info:
                        print(f"✓ Patient: {self.patient_info.get('name', 'Unknown')}, "
                              f"{self.patient_info.get('age', 'Unknown')}Y, "
                              f"{self.patient_info.get('sex', 'Unknown')}")
                
                # Extract biomarkers
                self.extract_biomarkers(pdf)
                print(f"✓ Extracted {len(self.biomarkers)} biomarkers")
                
                # Save results
                result = {**self.patient_info, **self.biomarkers}
                output_file = self.pdf_path.stem + '_final_extracted.json'
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                
                print(f"✓ Saved to: {output_file}")
                
                print(f"\n{'='*80}")
                print(f"EXTRACTION COMPLETE")
                print(f"{'='*80}\n")
                
                return result
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("\nUsage: python thyrocare_pdfplumber_final.py <pdf_file>\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"\n❌ Error: File not found: {pdf_path}\n")
        sys.exit(1)
    
    extractor = ThyrocareExtractorFinal(pdf_path)
    result = extractor.process()
    
    if result:
        biomarkers_only = {k: v for k, v in result.items() if k not in ['name', 'age', 'sex', 'cycle']}
        print(f"Sample of extracted biomarkers (first 40):")
        print("-" * 80)
        for i, (test, value) in enumerate(list(biomarkers_only.items())[:40], 1):
            print(f"{i:2d}. {test:<55} {value}")
        
        if len(biomarkers_only) > 40:
            print(f"\n... and {len(biomarkers_only) - 40} more biomarkers")


if __name__ == "__main__":
    main()


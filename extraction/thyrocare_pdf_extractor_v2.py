#!/usr/bin/env python3
"""
THYROCARE PDF Extractor v2 - Maximum accuracy with relaxed patterns
"""

import PyPDF2
import re
import json
import sys
from pathlib import Path


class ThyrocarePDFExtractorV2:
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
        # Remove technology/method names
        test_name = re.sub(r'\s+(PHOTOMETRY|E\.C\.L\.I\.A|C\.L\.I\.A|E\.L\.I\.S\.A|CALCULATED|H\.P\.L\.C|C\.M\.I\.A|LC-MS/MS|I\.S\.E\s*-\s*INDIRECT).*$', '', test_name, flags=re.IGNORECASE)
        test_name = re.sub(r'\s+(SLS-Hemoglobin Method|CPH Detection|HF & EI|Calculated|Flow Cytometry|Microscopy|Diazo coupling|Peroxidase reaction|Esterase reaction|GOD-POD|PEI|Hays sulphur|Ehrlich reaction).*$', '', test_name, flags=re.IGNORECASE)
        test_name = ' '.join(test_name.split())
        return test_name.strip()
    
    def extract_biomarkers(self):
        """Extract all biomarkers with comprehensive pattern matching."""
        
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # Try each extraction pattern
            extracted = None
            
            # Pattern 1: Table format (TEST NAME UNITS VALUE TECHNOLOGY)
            if 'TEST NAME' in line and 'VALUE' in line:
                i += 1
                if i < len(self.lines):
                    value_line = self.lines[i].strip()
                    value_match = re.search(r'([\w/µ³]+)\s+([\d\.]+|NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT)', value_line, re.IGNORECASE)
                    if value_match:
                        value = value_match.group(2)
                        i += 1
                        if i < len(self.lines):
                            test_line = self.lines[i].strip()
                            test_match = re.search(r'Bio\.\s*Ref\.\s*Interval\.\s*:-(.+?)(?:\s+[A-Z\.]{5,}\s*$|$)', test_line)
                            if test_match:
                                test_name = self.normalize_test_name(test_match.group(1).strip())
                                if test_name:
                                    self.biomarkers[test_name] = value
                i += 1
                continue
            
            # Pattern 2: VALUE TEST_NAME REF UNITS
            match = re.match(r'^([\d\.]+)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+[\d\<\>]', line)
            if match and not extracted:
                value = match.group(1)
                test_name = self.normalize_test_name(match.group(2).strip())
                if test_name and len(test_name) > 3:
                    self.biomarkers[test_name] = value
                    extracted = True
            
            # Pattern 3: REF UNITS  VALUE TECHNOLOGY TEST_NAME
            if not extracted:
                match = re.match(r'[\<\>]?\s*\d+\.?\d*\s+[\w/]+\s+([\d\.]+)\s+[\w\.\s\-]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line)
                if match:
                    value = match.group(1)
                    test_name = self.normalize_test_name(match.group(2).strip())
                    if test_name and len(test_name) > 3:
                        self.biomarkers[test_name] = value
                        extracted = True
            
            # Pattern 4: UNITS  VALUE REF TEST_NAME
            if not extracted:
                match = re.match(r'^([\w/µ³Â]+)\s+([\d\.]+)\s+[\d\.\-\s]+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line)
                if match:
                    value = match.group(2)
                    test_name = self.normalize_test_name(match.group(3).strip())
                    if test_name and len(test_name) > 5:
                        self.biomarkers[test_name] = value
                        extracted = True
            
            # Pattern 5: % VALUE TECHNOLOGY TEST_NAME
            if not extracted:
                match = re.match(r'^%\s+([\d\.]+)\s+[\w\.\-]+\s+([A-Z][A-Za-z0-9\s\-\(\)]+)', line)
                if match:
                    value = match.group(1)
                    test_name = self.normalize_test_name(match.group(2).strip())
                    if test_name:
                        self.biomarkers[test_name] = value
                        extracted = True
            
            # Pattern 6: TEST_NAME QUALITATIVE_VALUE
            if not extracted:
                match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,}?)\s+(ABSENT|PRESENT|NORMAL|NIL|TRACE|SLIGHT CLOUDY|PALE YELLOW|CLEAR|NON REACTIVE|REACTIVE)\s', line, re.IGNORECASE)
                if match:
                    test_name = self.normalize_test_name(match.group(1).strip())
                    value = match.group(2).upper()
                    if test_name:
                        self.biomarkers[test_name] = value
                        extracted = True
            
            # Pattern 7: QUALITATIVE_VALUE TEST_NAME
            if not extracted:
                match = re.match(r'^(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line, re.IGNORECASE)
                if match:
                    value = match.group(1).upper()
                    test_name = self.normalize_test_name(match.group(2).strip())
                    if test_name:
                        self.biomarkers[test_name] = value
                        extracted = True
            
            # Pattern 8: UNITS VALUE TECHNOLOGY TEST_NAME (relaxed)
            if not extracted:
                match = re.match(r'^([\w/µ³]+)\s+([\d\.]+)\s+([\w\.\s\-]+?)\s+([A-Z][A-Z\s\-\(\)\/]+)', line)
                if match:
                    value = match.group(2)
                    test_name = self.normalize_test_name(match.group(4).strip())
                    if test_name and len(test_name) > 5 and not any(x in test_name for x in ['Bio', 'Ref', 'Interval']):
                        self.biomarkers[test_name] = value
                        extracted = True
            
            # Pattern 9: REF-REF UNITS  VALUE TECHNOLOGY TEST_NAME
            if not extracted:
                match = re.match(r'^[\d\.\-<>]+\s+[\w/]+\s+([\d\.]+)\s+[\w\.\s\-]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line)
                if match:
                    value = match.group(1)
                    test_name = self.normalize_test_name(match.group(2).strip())
                    if test_name and len(test_name) > 5:
                        self.biomarkers[test_name] = value
                        extracted = True
            
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
        print(f"THYROCARE PDF EXTRACTOR V2")
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
        print("\nUsage: python thyrocare_pdf_extractor_v2.py <pdf_file>\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"\n❌ Error: File not found: {pdf_path}\n")
        sys.exit(1)
    
    extractor = ThyrocarePDFExtractorV2(pdf_path)
    result = extractor.process()
    
    if result:
        biomarkers_only = {k: v for k, v in result.items() if k not in ['name', 'age', 'sex', 'cycle']}
        print(f"Sample of extracted biomarkers (first 30):")
        print("-" * 80)
        for i, (test, value) in enumerate(list(biomarkers_only.items())[:30], 1):
            print(f"{i:2d}. {test:<55} {value}")
        
        if len(biomarkers_only) > 30:
            print(f"\n... and {len(biomarkers_only) - 30} more biomarkers")


if __name__ == "__main__":
    main()

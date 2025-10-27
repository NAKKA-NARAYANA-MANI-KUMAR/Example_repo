#!/usr/bin/env python3
"""
THYROCARE PDF Extractor using pdfplumber
High-accuracy biomarker extraction with table structure preservation
"""

import pdfplumber
import re
import json
import sys
from pathlib import Path


class ThyrocareExtractorPlumber:
    """Extract biomarkers from THYROCARE PDF using pdfplumber."""
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.patient_info = {}
        self.biomarkers = {}
        self.all_text = ""
        
    def extract_patient_info(self, first_page_text):
        """Extract patient demographics from first page."""
        patterns = [
            r'([A-Z][A-Z\s]+?)\s*\((\d+)\s*Y?\s*/\s*([MF])\)',
            r'([A-Z][A-Z\s]+?)\s+(\d+)\s*Y\s*/\s*([MF])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, first_page_text)
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
        
        # Remove technology/method suffixes
        name = re.sub(r'\s+(PHOTOMETRY|E\.C\.L\.I\.A|C\.L\.I\.A|E\.L\.I\.S\.A|CALCULATED|H\.P\.L\.C|C\.M\.I\.A|LC-MS/MS|I\.S\.E\s*-?\s*INDIRECT).*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(SLS-Hemoglobin Method|CPH Detection|HF & EI|Calculated|Flow Cytometry|Microscopy).*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+(Diazo coupling|Peroxidase reaction|Esterase reaction|GOD-POD|PEI|Hays sulphur|Ehrlich reaction).*$', '', name, flags=re.IGNORECASE)
        
        # Clean whitespace
        name = ' '.join(name.split())
        name = name.strip()
        
        # Filter out non-test names
        if len(name) < 4:
            return None
        if any(x in name.lower() for x in ['bio.', 'ref.', 'interval', 'clinical', 'page', 'tested', 'report']):
            return None
        
        return name
    
    def is_valid_value(self, value):
        """Check if value looks like a test result."""
        if not value:
            return False
        
        value_str = str(value).strip()
        
        # Valid qualitative values
        qualitative = ['ABSENT', 'PRESENT', 'POSITIVE', 'NEGATIVE', 'REACTIVE', 'NON REACTIVE', 
                      'NORMAL', 'ABNORMAL', 'NIL', 'TRACE', 'CLEAR', 'SLIGHT CLOUDY', 'PALE YELLOW']
        if any(q in value_str.upper() for q in qualitative):
            return True
        
        # Valid numeric values
        try:
            num = float(value_str)
            # Reasonable range for medical values
            if 0 <= num <= 100000:
                return True
        except:
            pass
        
        return False
    
    def extract_from_tables(self, pdf):
        """Extract biomarkers from table structures."""
        print("Extracting from tables...")
        
        for page_num, page in enumerate(pdf.pages, 1):
            # Extract tables from page
            tables = page.extract_tables()
            
            for table in tables:
                if not table:
                    continue
                
                # Try to identify table structure
                for row in table:
                    if not row or len(row) < 2:
                        continue
                    
                    # Skip header rows
                    if any(x and 'TEST NAME' in str(x).upper() for x in row):
                        continue
                    
                    # Try different column layouts
                    # Layout 1: [TEST_NAME, VALUE, UNITS, REF]
                    # Layout 2: [TEST_NAME, UNITS, VALUE, REF]
                    # Layout 3: [UNITS, VALUE, REF, TEST_NAME]
                    
                    for i in range(len(row)):
                        cell = row[i]
                        if cell and isinstance(cell, str) and len(cell) > 3:
                            test_name = self.clean_test_name(cell)
                            if test_name:
                                # Look for value in adjacent cells
                                for j in range(max(0, i-2), min(len(row), i+3)):
                                    if j != i and row[j]:
                                        value = str(row[j]).strip()
                                        if self.is_valid_value(value):
                                            # Store the biomarker
                                            if test_name not in self.biomarkers:
                                                self.biomarkers[test_name] = value
                                            break
    
    def extract_from_text(self, pdf):
        """Extract biomarkers from plain text with pattern matching."""
        print("Extracting from text patterns...")
        
        all_text = ""
        for page in pdf.pages:
            all_text += page.extract_text() + "\n"
        
        self.all_text = all_text
        lines = all_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Pattern 1: VALUE TEST_NAME REF UNITS
            match = re.match(r'^([\d\.]+)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]+?)\s+[\d\<\>]', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 2: TEST_NAME QUALITATIVE_VALUE
            match = re.match(r'^([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,}?)\s+(ABSENT|PRESENT|POSITIVE|NEGATIVE|REACTIVE|NON REACTIVE|NORMAL|ABNORMAL|NIL|TRACE|CLEAR|SLIGHT CLOUDY|PALE YELLOW)\s', line, re.IGNORECASE)
            if match:
                test_name = self.clean_test_name(match.group(1))
                value = match.group(2).upper()
                if test_name and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 3: QUALITATIVE_VALUE TEST_NAME
            match = re.match(r'^(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE|NORMAL|ABNORMAL|SLIGHT CLOUDY|PALE YELLOW|CLEAR)\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line, re.IGNORECASE)
            if match:
                value = match.group(1).upper()
                test_name = self.clean_test_name(match.group(2))
                if test_name and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 4: REF UNITS  VALUE TECHNOLOGY TEST_NAME
            match = re.match(r'[\<\>]?\s*[\d\.\-]+\s+[\w/µ³]+\s+([\d\.]+)\s+[\w\.\s\-]+\s+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 5: UNITS  VALUE REF TEST_NAME
            match = re.match(r'^([\w/µ³%]+)\s+([\d\.]+)\s+[\d\.\-\s]+([A-Z][A-Z0-9\s\-\(\)\/,\.]{5,})', line)
            if match:
                value = match.group(2)
                test_name = self.clean_test_name(match.group(3))
                if test_name and len(test_name) > 5 and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 6: % VALUE TECHNOLOGY TEST_NAME
            match = re.match(r'^%\s+([\d\.]+)\s+[\w\.\-]+\s+([A-Z][A-Za-z0-9\s\-\(\)]+)', line)
            if match:
                value = match.group(1)
                test_name = self.clean_test_name(match.group(2))
                if test_name and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
            
            # Pattern 7: UNITS VALUE TECHNOLOGY TEST_NAME
            match = re.match(r'^([\w/µ³]+)\s+([\d\.]+)\s+([\w\.\s\-]+?)\s+([A-Z][A-Z\s\-\(\)\/]{10,})', line)
            if match:
                value = match.group(2)
                test_name = self.clean_test_name(match.group(4))
                if test_name and test_name not in self.biomarkers:
                    self.biomarkers[test_name] = value
                continue
    
    def process(self):
        """Main processing pipeline."""
        print(f"\n{'='*80}")
        print(f"THYROCARE PDF EXTRACTOR (pdfplumber)")
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
                
                # Extract biomarkers from tables
                self.extract_from_tables(pdf)
                print(f"  → Found {len(self.biomarkers)} biomarkers from tables")
                
                # Extract biomarkers from text patterns
                table_count = len(self.biomarkers)
                self.extract_from_text(pdf)
                text_count = len(self.biomarkers) - table_count
                print(f"  → Found {text_count} additional biomarkers from text")
                
                print(f"\n✓ Total extracted: {len(self.biomarkers)} biomarkers")
                
                # Save results
                result = {**self.patient_info, **self.biomarkers}
                output_file = self.pdf_path.stem + '_pdfplumber_extracted.json'
                
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
        print("\n" + "="*80)
        print("THYROCARE PDF BIOMARKER EXTRACTOR (pdfplumber)")
        print("="*80)
        print("\nUsage: python thyrocare_extractor_pdfplumber.py <pdf_file>")
        print("\nExample:")
        print("  python thyrocare_extractor_pdfplumber.py report.pdf")
        print("\nOutput:")
        print("  Creates a JSON file with extracted biomarkers")
        print("="*80 + "\n")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"\n❌ Error: File not found: {pdf_path}\n")
        sys.exit(1)
    
    extractor = ThyrocareExtractorPlumber(pdf_path)
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


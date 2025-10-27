#!/usr/bin/env python3
"""
Medical Lab Report Biomarker Extractor
Extracts biomarker values from PDF medical reports and converts to standardized JSON format.
"""

import re
import json
import sys
from pathlib import Path
try:
    import PyPDF2
except ImportError:
    print("Error: PyPDF2 not installed. Install with: pip install PyPDF2")
    sys.exit(1)


class BiomarkerExtractor:
    """Extract and standardize biomarker data from medical lab reports."""
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.text = ""
        self.biomarkers = {}
        self.patient_info = {}
        
    def extract_text_from_pdf(self):
        """Extract all text from PDF file."""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                self.text = ""
                for page in reader.pages:
                    self.text += page.extract_text() + "\n"
            print(f"✓ Extracted text from {len(reader.pages)} pages")
            return True
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return False
    
    def extract_patient_info(self):
        """Extract patient demographic information."""
        # Extract name
        name_match = re.search(r'([A-Z\s]+)\s*\((\d+)Y/([MF])\)', self.text)
        if name_match:
            self.patient_info['name'] = name_match.group(1).strip()
            self.patient_info['age'] = int(name_match.group(2))
            self.patient_info['sex'] = 'Male' if name_match.group(3) == 'M' else 'Female'
            self.patient_info['cycle'] = 'All'
            print(f"✓ Patient: {self.patient_info['name']}, {self.patient_info['age']}Y, {self.patient_info['sex']}")
        else:
            print("⚠ Could not extract patient info")
    
    def find_value_near_test(self, test_name, unit_hint=None, value_range=None):
        """Find numeric value near a test name in the text."""
        lines = self.text.split('\n')
        for i, line in enumerate(lines):
            if test_name in line:
                # Search nearby lines
                for j in range(max(0, i-10), min(len(lines), i+10)):
                    search_line = lines[j]
                    # Find numeric patterns
                    matches = re.findall(r'(\d+\.?\d*)', search_line)
                    for match in matches:
                        try:
                            value = float(match)
                            if value_range:
                                if value_range[0] <= value <= value_range[1]:
                                    return value
                            else:
                                return value
                        except ValueError:
                            continue
        return None
    
    def extract_hormones(self):
        """Extract hormone biomarkers."""
        hormone_tests = {
            'AMH': ('ANTI MULLERIAN HORMONE', 'ng/mL', (0.0, 20.0)),
            'DHT': ('DIHYDROTESTOSTERONE', 'pg/mL', (0.0, 2000.0)),
            'SHBG': ('SEX HORMONE BINDING GLOBULIN', 'nmol/L', (0.0, 200.0)),
            '17OH': ('17 OH PROGESTERONE', 'ng/mL', (0.0, 10.0)),
            'CPEP': ('C-PEPTIDE', 'ng/mL', (0.0, 10.0)),
            'FTES': ('FREE TESTOSTERONE', 'pg/mL', (0.0, 50.0)),
            'CORT': ('CORTISOL', 'µg/dL', (0.0, 50.0)),
            'DHEA': ('DHEA - SULPHATE', 'µg/dL', (0.0, 1000.0)),
            'PROG': ('PROGESTERONE', 'ng/mL', (0.0, 50.0)),
            'E2': ('ESTRADIOL', 'pg/mL', (0.0, 1000.0)),
            'FSH': ('FOLLICLE STIMULATING HORMONE', 'mIU/mL', (0.0, 200.0)),
            'LH': ('LUTEINISING HORMONE', 'mIU/mL', (0.0, 200.0)),
            'PRL': ('PROLACTIN', 'ng/mL', (0.0, 500.0)),
            'TEST': ('TESTOSTERONE', 'ng/dL', (0.0, 2000.0)),
        }
        
        for var_name, (test_name, unit, value_range) in hormone_tests.items():
            value = self.find_value_near_test(test_name, unit, value_range)
            if value is not None:
                self.biomarkers[var_name] = value
    
    def extract_thyroid(self):
        """Extract thyroid biomarkers."""
        thyroid_tests = {
            'FT3': ('FREE TRIIODOTHYRONINE', 'pg/mL', (0.0, 10.0)),
            'FT4': ('FREE THYROXINE', 'ng/dL', (0.0, 5.0)),
            'USTSH': ('TSH - ULTRASENSITIVE', 'µIU/mL', (0.0, 20.0)),
            'ATG': ('ANTI THYROGLOBULIN', 'IU/mL', (0.0, 100.0)),
        }
        
        for var_name, (test_name, unit, value_range) in thyroid_tests.items():
            value = self.find_value_near_test(test_name, unit, value_range)
            if value is not None:
                self.biomarkers[var_name] = value
    
    def extract_lipid_profile(self):
        """Extract lipid profile biomarkers."""
        lipid_tests = {
            'TOTAL_CHOLESTEROL': ('TOTAL CHOLESTEROL', 'mg/dL', (0.0, 500.0)),
            'CHOL': ('HDL CHOLESTEROL', 'mg/dL', (0.0, 200.0)),
            'LDL': ('LDL CHOLESTEROL', 'mg/dL', (0.0, 300.0)),
            'TRIG': ('TRIGLYCERIDES', 'mg/dL', (0.0, 500.0)),
            'VLDL': ('VLDL CHOLESTEROL', 'mg/dL', (0.0, 100.0)),
            'TC/H': ('TC/ HDL CHOLESTEROL RATIO', 'Ratio', (0.0, 10.0)),
            'TRI/H': ('TRIG / HDL RATIO', 'Ratio', (0.0, 10.0)),
            'LDL/': ('LDL / HDL RATIO', 'Ratio', (0.0, 10.0)),
            'HD/LD': ('HDL / LDL RATIO', 'Ratio', (0.0, 5.0)),
            'NHDL': ('NON-HDL CHOLESTEROL', 'mg/dL', (0.0, 400.0)),
            'APOA': ('APOLIPOPROTEIN - A1', 'mg/dL', (0.0, 300.0)),
            'APOB': ('APOLIPOPROTEIN - B', 'mg/dL', (0.0, 300.0)),
            'APB/': ('APO B / APO A1 RATIO', 'Ratio', (0.0, 5.0)),
            'LPA': ('Lipoprotein (a)', 'mg/dL', (0.0, 200.0)),
        }
        
        for var_name, (test_name, unit, value_range) in lipid_tests.items():
            value = self.find_value_near_test(test_name, unit, value_range)
            if value is not None:
                self.biomarkers[var_name] = value
    
    def extract_cbc(self):
        """Extract complete blood count parameters."""
        cbc_tests = {
            'HB': ('HEMOGLOBIN', 'g/dL', (0.0, 20.0)),
            'PCV': ('Hematocrit', '%', (0.0, 60.0)),
            'RBC': ('Total RBC', 'X 10^6/µL', (0.0, 10.0)),
            'MCV': ('Mean Corpuscular Volume', 'fL', (0.0, 150.0)),
            'MCH': ('Mean Corpuscular Hemoglobin', 'pg', (0.0, 50.0)),
            'MCHC': ('Mean Corp.Hemo. Conc', 'g/dL', (0.0, 50.0)),
            'RDWSD': ('Red Cell Distribution Width - SD', 'fL', (0.0, 100.0)),
            'RDCV': ('Red Cell Distribution Width', '%', (0.0, 30.0)),
            'LEUC': ('TOTAL LEUCOCYTE COUNT', 'X 10³ / µL', (0.0, 30.0)),
            'NEUT': ('Neutrophils Percentage', '%', (0.0, 100.0)),
            'LYMPH': ('Lymphocytes Percentage', '%', (0.0, 100.0)),
            'MONO': ('Monocytes Percentage', '%', (0.0, 100.0)),
            'EOS': ('Eosinophils Percentage', '%', (0.0, 100.0)),
            'BASO': ('Basophils Percentage', '%', (0.0, 100.0)),
            'ANEU': ('Neutrophils - Absolute Count', 'X 10³ / µL', (0.0, 20.0)),
            'ALYM': ('Lymphocytes - Absolute Count', 'X 10³ / µL', (0.0, 10.0)),
            'AMON': ('Monocytes - Absolute Count', 'X 10³ / µL', (0.0, 5.0)),
            'AEOS': ('Eosinophils - Absolute Count', 'X 10³ / µL', (0.0, 5.0)),
            'ABAS': ('Basophils - Absolute Count', 'X 10³ / µL', (0.0, 1.0)),
            'PLT': ('PLATELET COUNT', 'X 10³ / µL', (0.0, 1000.0)),
            'MPV': ('Mean Platelet Volume', 'fL', (0.0, 20.0)),
        }
        
        for var_name, (test_name, unit, value_range) in cbc_tests.items():
            value = self.find_value_near_test(test_name, unit, value_range)
            if value is not None:
                self.biomarkers[var_name] = value
    
    def extract_liver_kidney(self):
        """Extract liver and kidney function tests."""
        tests = {
            'ALKP': ('ALKALINE PHOSPHATASE', 'U/L', (0.0, 500.0)),
            'BILT': ('BILIRUBIN - TOTAL', 'mg/dL', (0.0, 10.0)),
            'BILD': ('BILIRUBIN -DIRECT', 'mg/dL', (0.0, 5.0)),
            'GGT': ('GAMMA GLUTAMYL TRANSFERASE', 'U/L', (0.0, 500.0)),
            'SGOT': ('ASPARTATE AMINOTRANSFERASE', 'U/L', (0.0, 500.0)),
            'SGPT': ('ALANINE TRANSAMINASE', 'U/L', (0.0, 500.0)),
            'PROT': ('PROTEIN - TOTAL', 'gm/dL', (0.0, 15.0)),
            'SALB': ('ALBUMIN - SERUM', 'gm/dL', (0.0, 10.0)),
            'BUN': ('BLOOD UREA NITROGEN', 'mg/dL', (0.0, 100.0)),
            'SCRE': ('CREATININE - SERUM', 'mg/dL', (0.0, 10.0)),
            'EGFR': ('GLOMERULAR FILTRATION RATE', 'mL/min', (0.0, 200.0)),
            'URIC': ('URIC ACID', 'mg/dL', (0.0, 20.0)),
        }
        
        for var_name, (test_name, unit, value_range) in tests.items():
            value = self.find_value_near_test(test_name, unit, value_range)
            if value is not None:
                self.biomarkers[var_name] = value
    
    def extract_metabolic(self):
        """Extract metabolic and nutrition markers."""
        tests = {
            'FBS': ('FASTING BLOOD SUGAR', 'mg/dL', (0.0, 500.0)),
            'HBA': ('HbA1c', '%', (0.0, 20.0)),
            'ABG': ('AVERAGE BLOOD GLUCOSE', 'mg/dL', (0.0, 500.0)),
            'INSFA': ('INSULIN - FASTING', 'µU/mL', (0.0, 200.0)),
            'HOMIR': ('HOMA INSULIN RESISTANCE', 'Index', (0.0, 20.0)),
            'VITDC': ('25-OH VITAMIN D', 'ng/mL', (0.0, 200.0)),
            'VITB': ('VITAMIN B-12', 'pg/mL', (0.0, 2000.0)),
            'FOLI': ('FOLATE', 'ng/mL', (0.0, 50.0)),
            'FERR': ('FERRITIN', 'ng/mL', (0.0, 1000.0)),
            'IRON': ('IRON', 'µg/dL', (0.0, 500.0)),
            'CALC': ('CALCIUM', 'mg/dL', (0.0, 20.0)),
            'MG': ('MAGNESIUM', 'mg/dL', (0.0, 10.0)),
        }
        
        for var_name, (test_name, unit, value_range) in tests.items():
            value = self.find_value_near_test(test_name, unit, value_range)
            if value is not None:
                self.biomarkers[var_name] = value
    
    def extract_all_biomarkers(self):
        """Extract all biomarker categories."""
        print("\n🔍 Extracting biomarkers...")
        
        self.extract_hormones()
        print(f"  ✓ Hormones: {sum(1 for k in self.biomarkers if k in ['AMH','DHT','SHBG','17OH','CPEP','FTES','CORT','DHEA','PROG','E2','FSH','LH','PRL','TEST'])}")
        
        self.extract_thyroid()
        print(f"  ✓ Thyroid: {sum(1 for k in self.biomarkers if k in ['FT3','FT4','USTSH','ATG'])}")
        
        self.extract_lipid_profile()
        print(f"  ✓ Lipid Profile: {sum(1 for k in self.biomarkers if k in ['TOTAL_CHOLESTEROL','CHOL','LDL','TRIG','VLDL','TC/H','TRI/H','LDL/','HD/LD','NHDL','APOA','APOB','APB/','LPA'])}")
        
        self.extract_cbc()
        print(f"  ✓ Complete Blood Count: {sum(1 for k in self.biomarkers if k in ['HB','PCV','RBC','MCV','MCH','MCHC','RDWSD','RDCV','LEUC','NEUT','LYMPH','MONO','EOS','BASO','ANEU','ALYM','AMON','AEOS','ABAS','PLT','MPV'])}")
        
        self.extract_liver_kidney()
        print(f"  ✓ Liver/Kidney: {sum(1 for k in self.biomarkers if k in ['ALKP','BILT','BILD','GGT','SGOT','SGPT','PROT','SALB','BUN','SCRE','EGFR','URIC'])}")
        
        self.extract_metabolic()
        print(f"  ✓ Metabolic: {sum(1 for k in self.biomarkers if k in ['FBS','HBA','ABG','INSFA','HOMIR','VITDC','VITB','FOLI','FERR','IRON','CALC','MG'])}")
        
        print(f"\n✓ Total biomarkers extracted: {len(self.biomarkers)}")
    
    def generate_json(self):
        """Generate final JSON output."""
        result = {**self.patient_info, **self.biomarkers}
        return result
    
    def save_json(self, output_path=None):
        """Save results to JSON file."""
        if output_path is None:
            output_path = self.pdf_path.stem + '_biomarkers.json'
        
        result = self.generate_json()
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Saved to: {output_path}")
        return output_path
    
    def process(self, save_output=True):
        """Main processing pipeline."""
        print(f"\n📄 Processing: {self.pdf_path.name}")
        print("=" * 60)
        
        if not self.extract_text_from_pdf():
            return None
        
        self.extract_patient_info()
        self.extract_all_biomarkers()
        
        if save_output:
            return self.save_json()
        else:
            return self.generate_json()


def main():
    """Command line interface."""
    if len(sys.argv) < 2:
        print("Usage: python pdf_biomarker_extractor.py <pdf_file>")
        print("Example: python pdf_biomarker_extractor.py report.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    extractor = BiomarkerExtractor(pdf_path)
    output_file = extractor.process()
    
    if output_file:
        print(f"\n✅ Success! Biomarkers extracted and saved.")
        print(f"📊 Open {output_file} to view results")
    else:
        print("\n❌ Failed to process PDF")
        sys.exit(1)


if __name__ == "__main__":
    main()


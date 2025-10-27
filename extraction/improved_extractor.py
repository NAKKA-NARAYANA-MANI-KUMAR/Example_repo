#!/usr/bin/env python3
"""
Improved Biomarker Extractor - Uses better table structure parsing
"""

import re
import json
import sys
from pathlib import Path
import PyPDF2


class ImprovedBiomarkerExtractor:
    """Extract biomarkers by parsing table structure in THYROCARE reports."""
    
    # Biomarker name mappings for matching
    BIOMARKER_ALIASES = {
        '25-OH VITAMIN D': '25-OH VITAMIN D (TOTAL)',
        'VITAMIN D': '25-OH VITAMIN D (TOTAL)',
        'VITAMIN D (TOTAL)': '25-OH VITAMIN D (TOTAL)',
        'ACTH': 'ADRENOCORTICOTROPIC HORMONE (ACTH)',
        'SGPT': 'ALANINE TRANSAMINASE (SGPT)',
        'ALT': 'ALANINE TRANSAMINASE (SGPT)',
        'ALBUMIN': 'ALBUMIN - SERUM',
        'SERUM ALBUMIN': 'ALBUMIN - SERUM',
        'ALP': 'ALKALINE PHOSPHATASE',
        'ALKP': 'ALKALINE PHOSPHATASE',
        'ACCP': 'ANTI CCP (ACCP)',
        'ANTI-CCP': 'ANTI CCP (ACCP)',
        'AMA': 'ANTI MICROSOMAL ANTIBODY (AMA)',
        'AMH': 'ANTI MULLERIAN HORMONE (AMH)',
        'ANA': 'ANTI NUCLEAR ANTIBODIES (ANA)',
        'ATG': 'ANTI THYROGLOBULIN ANTIBODY (ATG)',
        'ANTI-TPO': 'ANTI-THYROID PEROXIDASE ANTIBODIES',
        'APO B/A1': 'APO B / APO A1 RATIO (APO B/A1)',
        'APO-A1': 'APOLIPOPROTEIN - A1 (APO-A1)',
        'APOA1': 'APOLIPOPROTEIN - A1 (APO-A1)',
        'APO-B': 'APOLIPOPROTEIN - B (APO-B)',
        'APOB': 'APOLIPOPROTEIN - B (APO-B)',
        'SGOT': 'ASPARTATE AMINOTRANSFERASE (SGOT )',
        'AST': 'ASPARTATE AMINOTRANSFERASE (SGOT )',
        'ABG': 'AVERAGE BLOOD GLUCOSE (ABG)',
        'BASOPHILS': 'BASOPHILS - ABSOLUTE COUNT',
        'BETA-HCG': 'BETA HCG',
        'B-HCG': 'BETA HCG',
        'INDIRECT BILIRUBIN': 'BILIRUBIN (INDIRECT)',
        'DIRECT BILIRUBIN': 'BILIRUBIN - DIRECT',
        'TOTAL BILIRUBIN': 'BILIRUBIN - TOTAL',
        'BUN': 'BLOOD UREA NITROGEN (BUN)',
        'C-PEPTIDE': 'C-PEPTIDE',
        'C PEPTIDE': 'C-PEPTIDE',
        'CA125': 'CA 125',
        'CA15.3': 'CA 15.3',
        'CA19.9': 'CA 19.9',
        'CEA': 'CARCINO EMBRYONIC ANTIGEN (CEA)',
        'CHLORIDE': 'CHLORIDE',
        'CORTISOL': 'CORTISOL',
        'SERUM CREATININE': 'CREATININE - SERUM',
        'CREATININE': 'CREATININE - SERUM',
        'URINE CREATININE': 'CREATININE - URINE',
        'CPK': 'CREATININE PHOSPHOKINASE',
        'CK': 'CREATININE PHOSPHOKINASE',
        'CYSTATIN-C': 'CYSTATIN C',
        'DHEAS': 'DHEA - SULPHATE (DHEAS)',
        'DHEA-S': 'DHEA - SULPHATE (DHEAS)',
        'DHT': 'DIHYDROTESTOSTERONE (DHT)',
        'EOSINOPHILS': 'EOSINOPHILS - ABSOLUTE COUNT',
        'EPITHELIAL CELLS': 'EPITHELIAL CELLS',
        'EBV': 'EPSTEIN BARR VIRAL CAPSID ANTIGEN - IGG',
        'EGFR': 'EST. GLOMERULAR FILTRATION RATE (eGFR)',
        'E2': 'ESTRADIOL/OESTROGEN (E2)',
        'ESTRADIOL': 'ESTRADIOL/OESTROGEN (E2)',
        'FBS': 'FASTING BLOOD SUGAR(GLUCOSE)',
        'FASTING GLUCOSE': 'FASTING BLOOD SUGAR(GLUCOSE)',
        'FERRITIN': 'FERRITIN',
        'FOLATE': 'FOLATE',
        'FSH': 'FOLLICLE STIMULATING HORMONE (FSH)',
        'FREE T': 'FREE TESTOSTERONE',
        'FT4': 'FREE THYROXINE (FT4)',
        'FREE T4': 'FREE THYROXINE (FT4)',
        'FT3': 'FREE TRIIODOTHYRONINE (FT3)',
        'FREE T3': 'FREE TRIIODOTHYRONINE (FT3)',
        'GGT': 'GAMMA GLUTAMYL TRANSFERASE (GGT)',
        'HDL': 'HDL CHOLESTEROL - DIRECT',
        'HDL CHOLESTEROL': 'HDL CHOLESTEROL - DIRECT',
        'PCV': 'HEMATOCRIT (PCV)',
        'HEMATOCRIT': 'HEMATOCRIT (PCV)',
        'HAEMOGLOBIN': 'HEMOGLOBIN',
        'HB': 'HEMOGLOBIN',
        'HBSAG': 'HEPATITIS B SURFACE ANTIGEN(HBSAG) RAPID TEST',
        'HS-CRP': 'HIGH SENSITIVITY C-REACTIVE PROTEIN (HS-CRP)',
        'HOMA-IR': 'HOMA INSULIN RESISTANCE INDEX',
        'HOMOCYSTEINE': 'HOMOCYSTEINE',
        'HBA1C': 'HbA1c',
        'GLYCATED HEMOGLOBIN': 'HbA1c',
        'IG%': 'IMMATURE GRANULOCYTE PERCENTAGE (IG%)',
        'IG': 'IMMATURE GRANULOCYTES (IG)',
        'FASTING INSULIN': 'INSULIN - FASTING',
        'INSULIN': 'INSULIN - FASTING',
        'IGF-1': 'INSULIN LIKE GROWTH FACTOR 1',
        'IRON': 'IRON',
        'LDH': 'LACTATE DEHYDROGENASE (LDH)',
        'LDL': 'LDL CHOLESTEROL - DIRECT',
        'LDL CHOLESTEROL': 'LDL CHOLESTEROL - DIRECT',
        'LIPASE': 'LIPASE',
        'LP(A)': 'LIPOPROTEIN (a) [Lp(a)]',
        'LIPOPROTEIN A': 'LIPOPROTEIN (a) [Lp(a)]',
        'LH': 'LUTEINISING HORMONE (LH)',
        'LYMPHOCYTES': 'LYMPHOCYTES - ABSOLUTE COUNT',
        'MAGNESIUM': 'MAGNESIUM',
        'MG': 'MAGNESIUM',
        'MCHC': 'MEAN CORP.HEMO. CONC (MCHC)',
        'MCH': 'MEAN CORPUSCULAR HEMOGLOBIN (MCH)',
        'MCV': 'MEAN CORPUSCULAR VOLUME (MCV)',
        'MPV': 'MEAN PLATELET VOLUME (MPV)',
        'MONOCYTES': 'MONOCYTES - ABSOLUTE COUNT',
        'NEUTROPHILS': 'NEUTROPHILS - ABSOLUTE COUNT',
        'NON-HDL': 'NON-HDL CHOLESTEROL',
        'NON HDL': 'NON-HDL CHOLESTEROL',
        'NRBC%': 'NUCLEATED RED BLOOD CELLS %',
        'NRBC': 'NUCLEATED RED BLOOD CELLS',
        'PLATELETS': 'PLATELET COUNT',
        'PLT': 'PLATELET COUNT',
        'PDW': 'PLATELET DISTRIBUTION WIDTH (PDW)',
        'PLCR': 'PLATELET TO LARGE CELL RATIO (PLCR)',
        'PCT': 'PLATELETCRIT (PCT)',
        'POTASSIUM': 'POTASSIUM',
        'K': 'POTASSIUM',
        'PROGESTERONE': 'PROGESTERONE',
        'PROLACTIN': 'PROLACTIN (PRL)',
        'PRL': 'PROLACTIN (PRL)',
        'PSA': 'PROSTATE SPECIFIC ANTIGEN (PSA)',
        'TOTAL PROTEIN': 'PROTEIN - TOTAL',
        'PROTEIN': 'PROTEIN - TOTAL',
        'QUICKI': 'QUANTITATIVE INSULIN SENSITIVITY INDEX',
        'RDW-SD': 'RED CELL DISTRIBUTION WIDTH - SD (RDW-SD)',
        'RDW-CV': 'RED CELL DISTRIBUTION WIDTH (RDW - CV)',
        'RDW': 'RED CELL DISTRIBUTION WIDTH (RDW - CV)',
        'RF': 'RHEUMATOID FACTOR (RF)',
        'A/G RATIO': 'SERUM ALB/GLOBULIN RATIO',
        'GLOBULIN': 'SERUM GLOBULIN',
        'ZINC': 'SERUM ZINC',
        'SHBG': 'SEX HORMONE BINDING GLOBULIN (SHBG)',
        'SODIUM': 'SODIUM',
        'NA': 'SODIUM',
        'SPECIFIC GRAVITY': 'SPECIFIC GRAVITY',
        'TC/HDL': 'TC/ HDL CHOLESTEROL RATIO',
        'TESTOSTERONE': 'TESTOSTERONE',
        'TOTAL CHOLESTEROL': 'TOTAL CHOLESTEROL',
        'TIBC': 'TOTAL IRON BINDING CAPACITY',
        'WBC': 'TOTAL LEUCOCYTES COUNT (WBC)',
        'TLC': 'TOTAL LEUCOCYTES COUNT (WBC)',
        'RBC': 'TOTAL RBC',
        'TRANSFERRIN SATURATION': 'TRANSFERRIN SATURATION %',
        'TRIGLYCERIDES': 'TRIGLYCERIDES',
        'TG': 'TRIGLYCERIDES',
        'TSH': 'TSH - ULTRASENSITIVE',
        'UREA': 'UREA (CALCULATED)',
        'UA/C': 'URI. ALBUMIN/CREATININE RATIO (UA/C)',
        'ALBUMIN CREATININE RATIO': 'URI. ALBUMIN/CREATININE RATIO (UA/C)',
        'URIC ACID': 'URIC ACID',
        'MICROALBUMIN': 'URINARY MICROALBUMIN',
        'VITAMIN B12': 'VITAMIN B-12',
        'B12': 'VITAMIN B-12',
        'FOLIC ACID': 'VITAMIN B9/FOLIC ACID',
        'VITAMIN B9': 'VITAMIN B9/FOLIC ACID',
        'VLDL': 'VLDL CHOLESTEROL',
        '17-OH PROGESTERONE': '17 OH PROGESTERONE',
        '17 OHP': '17 OH PROGESTERONE',
    }
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.text = ""
        self.lines = []
        self.patient_info = {}
        self.biomarkers = {}
        
    def extract_text_from_pdf(self):
        """Extract all text from PDF file."""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                self.text = ""
                for page in reader.pages:
                    self.text += page.extract_text() + "\n"
                self.lines = self.text.split('\n')
            return True
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return False
    
    def extract_patient_info(self):
        """Extract patient demographic information."""
        # Try multiple patterns for name extraction
        patterns = [
            r'([A-Z][A-Z\s]+?)\s*\((\d+)\s*Y?\s*/\s*([MF])\)',
            r'([A-Z][A-Z\s]+?)\s+(\d+)\s*Y\s*/\s*([MF])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                self.patient_info['name'] = match.group(1).strip()
                self.patient_info['age'] = int(match.group(2))
                self.patient_info['sex'] = 'Male' if match.group(3) == 'M' else 'Female'
                self.patient_info['cycle'] = 'All'
                return
    
    def extract_value_from_table_line(self, line):
        """
        Extract value from a table line.
        THYROCARE format: TEST NAME | TECHNOLOGY | VALUE | UNITS
        """
        # Try to parse the line as a table row
        # Look for patterns like: "TEST_NAME    TECHNOLOGY    VALUE    UNITS"
        
        # First, try to find qualitative values
        qualitative_values = ['NON REACTIVE', 'REACTIVE', 'POSITIVE', 'NEGATIVE', 
                            'ABSENT', 'PRESENT', 'NIL', 'TRACE', 'NORMAL', 'ABNORMAL',
                            'DETECTED', 'NOT DETECTED', 'SLIGHT CLOUDY', 'PALE YELLOW', 'CLEAR']
        
        for qual_val in qualitative_values:
            if qual_val in line.upper():
                return qual_val
        
        # Extract numeric values - looking for the VALUE column
        # Split by multiple spaces to get columns
        parts = re.split(r'\s{2,}', line.strip())
        
        # Try to find a numeric value in the parts
        for i, part in enumerate(parts):
            # Skip first part (test name) and second part (technology)
            if i < 2:
                continue
                
            # Look for numeric values
            match = re.search(r'(\d+\.?\d*)', part)
            if match:
                try:
                    value = float(match.group(1))
                    # Validate it's a reasonable value (not a page number or year)
                    if 0 < value < 10000 or value == 0:
                        return value
                except:
                    continue
        
        return None
    
    def normalize_biomarker_name(self, name):
        """Normalize biomarker name to standard format."""
        name = name.strip().upper()
        
        # Direct match
        if name in self.BIOMARKER_ALIASES:
            return self.BIOMARKER_ALIASES[name]
        
        # Partial match
        for alias, standard in self.BIOMARKER_ALIASES.items():
            if alias in name or name in alias:
                return standard
        
        return None
    
    def extract_all_biomarkers(self):
        """Extract all biomarkers by parsing table structure."""
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            
            # Look for test names in the line
            for alias, standard_name in self.BIOMARKER_ALIASES.items():
                if alias.upper() in line.upper():
                    # Found a potential match, look for value in this line or next few lines
                    search_lines = [line] + self.lines[i+1:min(i+5, len(self.lines))]
                    
                    for search_line in search_lines:
                        value = self.extract_value_from_table_line(search_line)
                        if value is not None:
                            self.biomarkers[standard_name] = value
                            break
                    break
            
            i += 1
    
    def generate_json(self):
        """Generate final JSON output."""
        result = {**self.patient_info, **self.biomarkers}
        return result
    
    def save_json(self, output_path=None):
        """Save results to JSON file."""
        if output_path is None:
            output_path = self.pdf_path.stem + '_improved_biomarkers.json'
        
        result = self.generate_json()
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        return output_path
    
    def process(self, save_output=True):
        """Main processing pipeline."""
        print(f"Processing: {self.pdf_path.name}")
        
        if not self.extract_text_from_pdf():
            return None
        
        self.extract_patient_info()
        print(f"Patient: {self.patient_info.get('name', 'Unknown')}")
        
        self.extract_all_biomarkers()
        print(f"Biomarkers extracted: {len(self.biomarkers)}")
        
        if save_output:
            return self.save_json()
        else:
            return self.generate_json()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python improved_extractor.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    extractor = ImprovedBiomarkerExtractor(pdf_path)
    output_file = extractor.process()
    
    if output_file:
        print(f"\nSuccess! Saved to: {output_file}")
    else:
        print("\nFailed to process PDF")
        sys.exit(1)


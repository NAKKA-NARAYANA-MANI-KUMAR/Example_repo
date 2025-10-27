#!/usr/bin/env python3
"""
Enhanced Thyrocare Medical Report Biomarker Extractor
Specifically designed for Thyrocare lab report format
"""

import re
import json
import sys
from pathlib import Path
import PyPDF2


class ThyrocareExtractor:
    """Extract biomarkers from Thyrocare format reports."""
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.text = ""
        self.biomarkers = {}
        self.patient_info = {}
        
    def extract_text(self):
        """Extract all text from PDF."""
        try:
            with open(self.pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                self.text = ""
                for page in reader.pages:
                    self.text += page.extract_text() + "\n"
            print(f"✓ Extracted {len(reader.pages)} pages")
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def extract_patient_info(self):
        """Extract patient information."""
        # Extract name, age, sex
        match = re.search(r'([A-Z\s]+)\s*\((\d+)Y/([MF])\)', self.text)
        if match:
            self.patient_info = {
                'name': match.group(1).strip(),
                'age': int(match.group(2)),
                'sex': 'Male' if match.group(3) == 'M' else 'Female',
                'cycle': 'All'
            }
            print(f"✓ Patient: {self.patient_info['name']}, {self.patient_info['age']}Y, {self.patient_info['sex']}")
    
    def extract_thyrocare_value(self, test_name_pattern, variable_name):
        """
        Extract value using Thyrocare's specific format:
        TEST NAME UNITS VALUE TECHNOLOGY
        unit value
        """
        # Split into lines
        lines = self.text.split('\n')
        
        for i, line in enumerate(lines):
            # Look for the test name
            if re.search(test_name_pattern, line, re.IGNORECASE):
                # Check next few lines for the value pattern
                for j in range(i, min(i+15, len(lines))):
                    next_line = lines[j].strip()
                    
                    # Pattern: unit value (e.g., "pg/mL 272.73" or "nmol/L 15.2")
                    value_match = re.match(r'^([a-zA-Zµ/°%³²\s\-\.\(\)]+)\s+(\d+\.?\d*)$', next_line)
                    if value_match:
                        try:
                            value = float(value_match.group(2))
                            # Sanity check - value should be reasonable
                            if 0 < value < 100000:
                                return value
                        except ValueError:
                            continue
                    
                    # Alternative pattern: value on same line after "VALUE"
                    if 'VALUE' in lines[j]:
                        value_match2 = re.search(r'VALUE\s+.*?\s+(\d+\.?\d*)', lines[j])
                        if value_match2:
                            try:
                                return float(value_match2.group(1))
                            except ValueError:
                                continue
        
        return None
    
    def extract_all_biomarkers(self):
        """Extract all biomarkers using Thyrocare format."""
        print("\n🔍 Extracting biomarkers...")
        
        # Define all biomarkers with their test name patterns
        biomarker_patterns = {
            # Hormones
            'AMH': r'ANTI MULLERIAN HORMONE',
            'DHT': r'DIHYDROTESTOSTERONE',
            'SHBG': r'SEX HORMONE BINDING GLOBULIN',
            '17OH': r'17 OH PROGESTERONE',
            'CPEP': r'C-PEPTIDE',
            'FTES': r'FREE TESTOSTERONE',
            'CORT': r'CORTISOL',
            'DHEA': r'DHEA - SULPHATE',
            'PROG': r'PROGESTERONE',
            'E2': r'ESTRADIOL',
            'FSH': r'FOLLICLE STIMULATING HORMONE',
            'LH': r'LUTEINISING HORMONE',
            'PRL': r'PROLACTIN',
            'TEST': r'TESTOSTERONE(?!.*FREE)',
            'ACTH': r'ADRENOCORTICOTROPIC HORMONE',
            
            # Thyroid
            'FT3': r'FREE TRIIODOTHYRONINE|FT3',
            'FT4': r'FREE THYROXINE|FT4',
            'USTSH': r'TSH - ULTRASENSITIVE|USTSH',
            'ATG': r'ANTI THYROGLOBULIN ANTIBODY',
            'ANTI_TPO': r'Anti-TPO antibody|THYROID PEROXIDASE',
            
            # Growth factors
            'INGF1': r'INSULIN LIKE GROWTH FACTOR',
            
            # Metabolic
            'FBS': r'FASTING BLOOD SUGAR|GLUCOSE.*FASTING',
            'HBA': r'HbA1c',
            'ABG': r'AVERAGE BLOOD GLUCOSE',
            'INSFA': r'INSULIN.*FASTING',
            'HOMIR': r'HOMA INSULIN RESISTANCE',
            'QUICKI': r'QUANTITATIVE INSULIN SENSITIVITY',
            'VITDC': r'25-OH VITAMIN D|VITAMIN D.*TOTAL',
            'VITB': r'VITAMIN B\s*-?\s*12',
            'VITB9': r'VITAMIN B\s*9|FOLIC ACID',
            'FOLI': r'FOLATE',
            'FERR': r'FERRITIN',
            'IRON': r'^IRON$',
            'HOMO': r'HOMOCYSTEINE',
            
            # Lipids
            'TOTAL_CHOLESTEROL': r'TOTAL CHOLESTEROL',
            'CHOL': r'HDL CHOLESTEROL',
            'LDL': r'LDL CHOLESTEROL',
            'TRIG': r'TRIGLYCERIDES',
            'VLDL': r'VLDL CHOLESTEROL',
            'TC/H': r'TC.*HDL.*RATIO',
            'TRI/H': r'TRIG.*HDL RATIO',
            'LDL/': r'LDL.*HDL RATIO',
            'HD/LD': r'HDL.*LDL RATIO',
            'NHDL': r'NON-HDL CHOLESTEROL',
            'APOA': r'APOLIPOPROTEIN.*A',
            'APOB': r'APOLIPOPROTEIN.*B',
            'APB/': r'APO B.*APO A',
            'LPA': r'Lipoprotein.*\(a\)',
            
            # Liver
            'ALKP': r'ALKALINE PHOSPHATASE',
            'BILT': r'BILIRUBIN.*TOTAL',
            'BILD': r'BILIRUBIN.*DIRECT',
            'BILI': r'BILIRUBIN.*INDIRECT',
            'GGT': r'GAMMA GLUTAMYL',
            'SGOT': r'ASPARTATE AMINOTRANSFERASE|SGOT',
            'SGPT': r'ALANINE TRANSAMINASE|SGPT',
            'OT/PT': r'SGOT.*SGPT RATIO',
            'PROT': r'PROTEIN.*TOTAL',
            'SALB': r'ALBUMIN.*SERUM',
            'SEGB': r'SERUM GLOBULIN',
            'A/GR': r'ALB.*GLOBULIN RATIO',
            
            # Kidney
            'BUN': r'BLOOD UREA NITROGEN',
            'SCRE': r'CREATININE.*SERUM',
            'EGFR': r'GLOMERULAR FILTRATION RATE',
            'URIC': r'URIC ACID',
            
            # Electrolytes
            'CALC': r'CALCIUM',
            'MG': r'MAGNESIUM',
            'POT': r'POTASSIUM',
            'SOD': r'SODIUM',
            'CHL': r'CHLORIDE',
            
            # Inflammation
            'HSCRP': r'HIGH SENSITIVITY C.*REACTIVE',
            'ANA': r'ANTI NUCLEAR ANTIBODIES',
            'ACCP': r'ANTI CCP',
            'RFAC': r'RHEUMATOID FACTOR',
            
            # Enzymes
            'AMYL': r'AMYLASE',
            'LASE': r'LIPASE',
            'LDH': r'LACTATE DEHYDROGENASE',
            'CPK': r'CREATININE PHOSPHOKINASE',
            'ALDOS': r'ALDOSTERONE',
            
            # Tumor markers
            'AFP': r'ALPHA FETO PROTEIN',
            'CEA': r'CARCINO EMBRYONIC ANTIGEN',
            'PSA': r'PROSTATE SPECIFIC ANTIGEN',
            'C125': r'CA.*125',
            'C199': r'CA.*19.*9',
            'C153': r'CA.*15.*3',
            'BHCG': r'BETA HCG',
            'CALCT': r'CALCITONIN',
            
            # Urine
            'UALB': r'URINARY MICROALBUMIN',
            'UCRA': r'CREATININE.*URINE',
            'UA/C': r'ALBUMIN.*CREATININE RATIO',
            
            # Other
            'SEZN': r'SERUM ZINC',
            'CYST': r'CYSTATIN',
            'EBVCG': r'EPSTEIN BARR',
        }
        
        # Extract each biomarker
        for var_name, pattern in biomarker_patterns.items():
            value = self.extract_thyrocare_value(pattern, var_name)
            if value is not None:
                self.biomarkers[var_name] = value
        
        print(f"✓ Extracted {len(self.biomarkers)} biomarkers")
    
    def extract_cbc(self):
        """Extract CBC parameters using specific patterns."""
        print("🔍 Extracting CBC...")
        
        cbc_patterns = {
            'HB': r'HEMOGLOBIN',
            'PCV': r'HEMATOCRIT|PCV',
            'RBC': r'TOTAL RBC|RBC COUNT',
            'MCV': r'MEAN CORPUSCULAR VOLUME',
            'MCH': r'MEAN CORPUSCULAR HEMOGLOBIN(?!.*CONC)',
            'MCHC': r'MEAN.*HEMO.*CONC',
            'RDWSD': r'RED CELL DISTRIBUTION WIDTH.*SD',
            'RDCV': r'RED CELL DISTRIBUTION WIDTH.*CV',
            'RDWI': r'RED CELL DISTRIBUTION WIDTH INDEX',
            'MI': r'MENTZER INDEX',
            'LEUC': r'TOTAL LEUCOCYTE COUNT|WBC',
            'NEUT': r'NEUTROPHILS PERCENTAGE|NEUTROPHIL\s+%',
            'LYMPH': r'LYMPHOCYTES PERCENTAGE|LYMPHOCYTE\s+%',
            'MONO': r'MONOCYTES PERCENTAGE|MONOCYTE\s+%',
            'EOS': r'EOSINOPHILS PERCENTAGE|EOSINOPHIL\s+%',
            'BASO': r'BASOPHILS PERCENTAGE|BASOPHIL\s+%',
            'IG%': r'IMMATURE GRANULOCYTE PERCENTAGE',
            'NRBC%': r'NUCLEATED RED BLOOD CELLS\s+%',
            'ANEU': r'NEUTROPHILS.*ABSOLUTE COUNT',
            'ALYM': r'LYMPHOCYTES.*ABSOLUTE COUNT',
            'AMON': r'MONOCYTES.*ABSOLUTE COUNT',
            'AEOS': r'EOSINOPHILS.*ABSOLUTE COUNT',
            'ABAS': r'BASOPHILS.*ABSOLUTE COUNT',
            'IG': r'IMMATURE GRANULOCYTES.*ABSOLUTE|IG(?!%)',
            'NRBC': r'NUCLEATED RED BLOOD CELLS(?!.*%)',
            'PLT': r'PLATELET COUNT',
            'MPV': r'MEAN PLATELET VOLUME',
            'PDW': r'PLATELET DISTRIBUTION WIDTH',
            'PLCR': r'PLATELET.*LARGE CELL RATIO',
            'PCT': r'PLATELETCRIT',
        }
        
        for var_name, pattern in cbc_patterns.items():
            value = self.extract_thyrocare_value(pattern, var_name)
            if value is not None:
                self.biomarkers[var_name] = value
        
        print(f"✓ Added CBC parameters")
    
    def process(self):
        """Main processing pipeline."""
        print(f"\n📄 Processing: {self.pdf_path.name}")
        print("=" * 70)
        
        if not self.extract_text():
            return None
        
        self.extract_patient_info()
        self.extract_all_biomarkers()
        self.extract_cbc()
        
        # Combine patient info and biomarkers
        result = {**self.patient_info, **self.biomarkers}
        
        # Save to JSON
        output_file = self.pdf_path.stem + '_biomarkers.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Saved: {output_file}")
        print(f"✅ Total fields: {len(result)} (Patient: 4, Biomarkers: {len(self.biomarkers)})")
        
        return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python thyrocare_extractor.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    extractor = ThyrocareExtractor(pdf_path)
    result = extractor.process()
    
    if result:
        print(f"\n✅ Successfully extracted {len(result)-4} biomarkers!")
    else:
        print("\n❌ Extraction failed")
        sys.exit(1)


if __name__ == "__main__":
    main()


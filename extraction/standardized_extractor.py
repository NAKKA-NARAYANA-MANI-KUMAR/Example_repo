#!/usr/bin/env python3
"""
Standardized Medical Lab Report Biomarker Extractor
Extracts biomarkers with exact standardized names and units from THYROCARE reports.
"""

import re
import json
import sys
from pathlib import Path
import PyPDF2


class StandardizedBiomarkerExtractor:
    """Extract biomarkers using standardized THYROCARE naming convention."""
    
    # Standardized biomarker mapping: (search_pattern, standard_name, standard_unit, value_range)
    BIOMARKER_MAP = {
        # Hormones
        '17 OH PROGESTERONE': ('17 OH PROGESTERONE|17-OH PROGESTERONE|17OH', '17 OH PROGESTERONE', 'ng/mL', (0.0, 10.0)),
        'AMH': ('ANTI MULLERIAN HORMONE|AMH', 'ANTI MULLERIAN HORMONE (AMH)', 'ng/mL', (0.0, 20.0)),
        'DHEAS': ('DHEA.*SULPHATE|DHEAS', 'DHEA - SULPHATE (DHEAS)', 'μg/dL', (0.0, 1000.0)),
        'DHT': ('DIHYDROTESTOSTERONE|DHT', 'DIHYDROTESTOSTERONE (DHT)', 'pg/mL', (0.0, 2000.0)),
        'SHBG': ('SEX HORMONE BINDING GLOBULIN|SHBG', 'SEX HORMONE BINDING GLOBULIN (SHBG)', 'nmol/L', (0.0, 200.0)),
        'C-PEPTIDE': ('C-PEPTIDE|C PEPTIDE', 'C-PEPTIDE', 'ng/mL', (0.0, 10.0)),
        'FREE_TESTOSTERONE': ('FREE TESTOSTERONE', 'FREE TESTOSTERONE', 'pg/mL', (0.0, 50.0)),
        'TESTOSTERONE': ('TESTOSTERONE', 'TESTOSTERONE', 'ng/dl', (0.0, 2000.0)),
        'CORTISOL': ('CORTISOL', 'CORTISOL', 'µg/dl', (0.0, 50.0)),
        'PROGESTERONE': ('PROGESTERONE', 'PROGESTERONE', 'ng/mL', (0.0, 50.0)),
        'ESTRADIOL': ('ESTRADIOL|OESTROGEN|E2', 'ESTRADIOL/OESTROGEN (E2)', 'pg/mL', (0.0, 1000.0)),
        'FSH': ('FOLLICLE STIMULATING HORMONE|FSH', 'FOLLICLE STIMULATING HORMONE (FSH)', 'mIU/L', (0.0, 200.0)),
        'LH': ('LUTEINISING HORMONE|LUTEINIZING HORMONE|LH', 'LUTEINISING HORMONE (LH)', 'mIU/L', (0.0, 200.0)),
        'PROLACTIN': ('PROLACTIN|PRL', 'PROLACTIN (PRL)', 'ng/ml', (0.0, 500.0)),
        'ACTH': ('ADRENOCORTICOTROPIC HORMONE|ACTH', 'ADRENOCORTICOTROPIC HORMONE (ACTH)', 'pg/mL', (0.0, 200.0)),
        'CALCITONIN': ('CALCITONIN', 'CALCITONIN', 'pg/mL', (0.0, 100.0)),
        'INSULIN_FASTING': ('INSULIN.*FASTING|FASTING.*INSULIN', 'INSULIN - FASTING', 'μU/ml', (0.0, 200.0)),
        'INSULIN_LIKE_GROWTH': ('INSULIN LIKE GROWTH FACTOR|IGF', 'INSULIN LIKE GROWTH FACTOR 1', 'ng/mL', (0.0, 1000.0)),
        'BETA_HCG': ('BETA HCG|β-HCG', 'BETA HCG', 'mIU/mL', (0.0, 10000.0)),
        
        # Thyroid
        'FT3': ('FREE TRIIODOTHYRONINE|FT3|FREE T3', 'FREE TRIIODOTHYRONINE (FT3)', 'pg/mL', (0.0, 10.0)),
        'FT4': ('FREE THYROXINE|FT4|FREE T4', 'FREE THYROXINE (FT4)', 'ng/dl', (0.0, 5.0)),
        'TSH': ('TSH.*ULTRASENSITIVE|TSH', 'TSH - ULTRASENSITIVE', 'μIU/mL', (0.0, 20.0)),
        'ATG': ('ANTI THYROGLOBULIN|ATG', 'ANTI THYROGLOBULIN ANTIBODY (ATG)', 'IU/ml', (0.0, 500.0)),
        'ANTI_TPO': ('ANTI.*THYROID PEROXIDASE|ANTI.*TPO', 'ANTI-THYROID PEROXIDASE ANTIBODIES', 'IU/mL', (0.0, 1000.0)),
        'AMA': ('ANTI MICROSOMAL ANTIBODY|AMA', 'ANTI MICROSOMAL ANTIBODY (AMA)', 'IU/mL', (0.0, 1000.0)),
        
        # Lipid Profile
        'TOTAL_CHOLESTEROL': ('TOTAL CHOLESTEROL', 'TOTAL CHOLESTEROL', 'mg/dl', (0.0, 500.0)),
        'HDL': ('HDL CHOLESTEROL', 'HDL CHOLESTEROL - DIRECT', 'mg/dL', (0.0, 200.0)),
        'LDL': ('LDL CHOLESTEROL', 'LDL CHOLESTEROL - DIRECT', 'mg/dL', (0.0, 300.0)),
        'TRIGLYCERIDES': ('TRIGLYCERIDES', 'TRIGLYCERIDES', 'mg/dL', (0.0, 1000.0)),
        'VLDL': ('VLDL CHOLESTEROL', 'VLDL CHOLESTEROL', 'mg/dL', (0.0, 100.0)),
        'NON_HDL': ('NON.*HDL CHOLESTEROL', 'NON-HDL CHOLESTEROL', 'mg/dL', (0.0, 400.0)),
        'TC_HDL_RATIO': ('TC.*HDL.*RATIO|TOTAL CHOLESTEROL.*HDL.*RATIO', 'TC/ HDL CHOLESTEROL RATIO', 'Ratio', (0.0, 10.0)),
        'TRIG_HDL_RATIO': ('TRIG.*HDL.*RATIO', 'TRIG / HDL RATIO', 'Ratio', (0.0, 10.0)),
        'LDL_HDL_RATIO': ('LDL.*HDL.*RATIO', 'LDL / HDL RATIO', 'Ratio', (0.0, 10.0)),
        'HDL_LDL_RATIO': ('HDL.*LDL.*RATIO', 'HDL / LDL RATIO', 'Ratio', (0.0, 5.0)),
        'APOA1': ('APOLIPOPROTEIN.*A1|APO.*A1', 'APOLIPOPROTEIN - A1 (APO-A1)', 'mg/dL', (0.0, 300.0)),
        'APOB': ('APOLIPOPROTEIN.*B[^/]|APO.*B[^/]', 'APOLIPOPROTEIN - B (APO-B)', 'mg/dL', (0.0, 300.0)),
        'APOB_A1_RATIO': ('APO.*B.*A1.*RATIO', 'APO B / APO A1 RATIO (APO B/A1)', 'Ratio', (0.0, 5.0)),
        'LIPOPROTEIN_A': ('LIPOPROTEIN.*\\(a\\)|LP\\(A\\)', 'LIPOPROTEIN (a) [Lp(a)]', 'mg/dl', (0.0, 200.0)),
        
        # Complete Blood Count
        'HEMOGLOBIN': ('HEMOGLOBIN|HAEMOGLOBIN', 'HEMOGLOBIN', 'g/dl', (0.0, 20.0)),
        'HEMATOCRIT': ('HEMATOCRIT|HAEMATOCRIT|PCV|PACKED CELL VOLUME', 'HEMATOCRIT (PCV)', '%', (0.0, 60.0)),
        'TOTAL_RBC': ('TOTAL RBC|RED BLOOD CELL COUNT', 'TOTAL RBC', 'X 10^6/μL', (0.0, 10.0)),
        'MCV': ('MEAN CORPUSCULAR VOLUME|MCV', 'MEAN CORPUSCULAR VOLUME (MCV)', 'fL', (0.0, 150.0)),
        'MCH': ('MEAN CORPUSCULAR HEMOGLOBIN[^C]|MCH[^C]', 'MEAN CORPUSCULAR HEMOGLOBIN (MCH)', 'pg', (0.0, 50.0)),
        'MCHC': ('MEAN CORP.*HEMO.*CONC|MCHC', 'MEAN CORP.HEMO. CONC (MCHC)', 'g/dL', (0.0, 50.0)),
        'RDW_SD': ('RED CELL DISTRIBUTION WIDTH.*SD|RDW.*SD', 'RED CELL DISTRIBUTION WIDTH - SD (RDW-SD)', 'fL', (0.0, 100.0)),
        'RDW_CV': ('RED CELL DISTRIBUTION WIDTH|RDW.*CV', 'RED CELL DISTRIBUTION WIDTH (RDW - CV)', '%', (0.0, 30.0)),
        'WBC': ('TOTAL LEUCOCYTE COUNT|TOTAL.*WBC|WBC', 'TOTAL LEUCOCYTES COUNT (WBC)', 'X 10^3/μL', (0.0, 30.0)),
        'NEUTROPHILS_PCT': ('NEUTROPHILS.*PERCENTAGE|NEUTROPHILS.*%', 'NEUTROPHILS PERCENTAGE', '%', (0.0, 100.0)),
        'LYMPHOCYTES_PCT': ('LYMPHOCYTES.*PERCENTAGE|LYMPHOCYTES.*%', 'LYMPHOCYTES PERCENTAGE', '%', (0.0, 100.0)),
        'MONOCYTES_PCT': ('MONOCYTES.*PERCENTAGE|MONOCYTES.*%', 'MONOCYTES PERCENTAGE', '%', (0.0, 100.0)),
        'EOSINOPHILS_PCT': ('EOSINOPHILS.*PERCENTAGE|EOSINOPHILS.*%', 'EOSINOPHILS PERCENTAGE', '%', (0.0, 100.0)),
        'BASOPHILS_PCT': ('BASOPHILS.*PERCENTAGE|BASOPHILS.*%', 'BASOPHILS PERCENTAGE', '%', (0.0, 100.0)),
        'NEUTROPHILS_ABS': ('NEUTROPHILS.*ABSOLUTE|ABSOLUTE.*NEUTROPHILS', 'NEUTROPHILS - ABSOLUTE COUNT', 'X 10³ / µL', (0.0, 20.0)),
        'LYMPHOCYTES_ABS': ('LYMPHOCYTES.*ABSOLUTE|ABSOLUTE.*LYMPHOCYTES', 'LYMPHOCYTES - ABSOLUTE COUNT', 'X 10³ / µL', (0.0, 10.0)),
        'MONOCYTES_ABS': ('MONOCYTES.*ABSOLUTE|ABSOLUTE.*MONOCYTES', 'MONOCYTES - ABSOLUTE COUNT', 'X 10³ / µL', (0.0, 5.0)),
        'EOSINOPHILS_ABS': ('EOSINOPHILS.*ABSOLUTE|ABSOLUTE.*EOSINOPHILS', 'EOSINOPHILS - ABSOLUTE COUNT', 'X 10³ / µL', (0.0, 5.0)),
        'BASOPHILS_ABS': ('BASOPHILS.*ABSOLUTE|ABSOLUTE.*BASOPHILS', 'BASOPHILS - ABSOLUTE COUNT', 'X 10³ / µL', (0.0, 1.0)),
        'PLATELET_COUNT': ('PLATELET COUNT', 'PLATELET COUNT', 'X 10³ / µL', (0.0, 1000.0)),
        'MPV': ('MEAN PLATELET VOLUME|MPV', 'MEAN PLATELET VOLUME (MPV)', 'fL', (0.0, 20.0)),
        'PDW': ('PLATELET DISTRIBUTION WIDTH|PDW', 'PLATELET DISTRIBUTION WIDTH (PDW)', 'fL', (0.0, 30.0)),
        'PCT': ('PLATELETCRIT|PCT', 'PLATELETCRIT (PCT)', '%', (0.0, 5.0)),
        'PLCR': ('PLATELET TO LARGE CELL RATIO|PLCR', 'PLATELET TO LARGE CELL RATIO (PLCR)', '%', (0.0, 100.0)),
        'IG_PCT': ('IMMATURE GRANULOCYTE PERCENTAGE|IG.*%', 'IMMATURE GRANULOCYTE PERCENTAGE (IG%)', '%', (0.0, 10.0)),
        'IG_ABS': ('IMMATURE GRANULOCYTES[^%]|IG[^%]', 'IMMATURE GRANULOCYTES (IG)', 'X 10³ / µL', (0.0, 1.0)),
        'NRBC_PCT': ('NUCLEATED RED BLOOD CELLS.*%', 'NUCLEATED RED BLOOD CELLS %', '%', (0.0, 10.0)),
        'NRBC_ABS': ('NUCLEATED RED BLOOD CELLS[^%]', 'NUCLEATED RED BLOOD CELLS', 'X 10³ / µL', (0.0, 1.0)),
        
        # Liver Function
        'SGPT': ('ALANINE TRANSAMINASE|SGPT|ALT', 'ALANINE TRANSAMINASE (SGPT)', 'U/L', (0.0, 500.0)),
        'SGOT': ('ASPARTATE AMINOTRANSFERASE|SGOT|AST', 'ASPARTATE AMINOTRANSFERASE (SGOT )', 'U/L', (0.0, 500.0)),
        'SGOT_SGPT_RATIO': ('SGOT.*SGPT.*RATIO|AST.*ALT.*RATIO', 'SGOT / SGPT RATIO', 'Ratio', (0.0, 10.0)),
        'ALKALINE_PHOSPHATASE': ('ALKALINE PHOSPHATASE|ALP', 'ALKALINE PHOSPHATASE', 'U/L', (0.0, 500.0)),
        'BILIRUBIN_TOTAL': ('BILIRUBIN.*TOTAL|TOTAL.*BILIRUBIN', 'BILIRUBIN - TOTAL', 'mg/dL', (0.0, 10.0)),
        'BILIRUBIN_DIRECT': ('BILIRUBIN.*DIRECT|DIRECT.*BILIRUBIN', 'BILIRUBIN - DIRECT', 'mg/dL', (0.0, 5.0)),
        'BILIRUBIN_INDIRECT': ('BILIRUBIN.*INDIRECT|INDIRECT.*BILIRUBIN', 'BILIRUBIN (INDIRECT)', 'mg/dL', (0.0, 5.0)),
        'GGT': ('GAMMA GLUTAMYL TRANSFERASE|GGT', 'GAMMA GLUTAMYL TRANSFERASE (GGT)', 'U/L', (0.0, 500.0)),
        'PROTEIN_TOTAL': ('PROTEIN.*TOTAL|TOTAL.*PROTEIN', 'PROTEIN - TOTAL', 'gm/dL', (0.0, 15.0)),
        'ALBUMIN_SERUM': ('ALBUMIN.*SERUM|SERUM.*ALBUMIN', 'ALBUMIN - SERUM', 'gm/dL', (0.0, 10.0)),
        'GLOBULIN': ('SERUM GLOBULIN|GLOBULIN', 'SERUM GLOBULIN', 'gm/dL', (0.0, 10.0)),
        'AG_RATIO': ('ALB.*GLOBULIN RATIO|A.*G.*RATIO', 'SERUM ALB/GLOBULIN RATIO', 'Ratio', (0.0, 5.0)),
        
        # Kidney Function
        'BUN': ('BLOOD UREA NITROGEN|BUN', 'BLOOD UREA NITROGEN (BUN)', 'mg/dL', (0.0, 100.0)),
        'CREATININE_SERUM': ('CREATININE.*SERUM|SERUM.*CREATININE', 'CREATININE - SERUM', 'mg/dL', (0.0, 10.0)),
        'UREA': ('UREA.*CALCULATED|UREA', 'UREA (CALCULATED)', 'mg/dL', (0.0, 200.0)),
        'BUN_CREATININE_RATIO': ('BUN.*CREATININE.*RATIO|BUN.*SR.*CREATININE.*RATIO', 'BUN / Sr.CREATININE RATIO', 'Ratio', (0.0, 50.0)),
        'UREA_CREATININE_RATIO': ('UREA.*SR.*CREATININE.*RATIO', 'UREA / SR.CREATININE RATIO', 'Ratio', (0.0, 100.0)),
        'EGFR': ('GLOMERULAR FILTRATION RATE|eGFR|EGFR', 'EST. GLOMERULAR FILTRATION RATE (eGFR)', 'mL/min/1.73 m2', (0.0, 200.0)),
        'URIC_ACID': ('URIC ACID', 'URIC ACID', 'mg/dL', (0.0, 20.0)),
        'CYSTATIN_C': ('CYSTATIN C', 'CYSTATIN C', 'mg/L', (0.0, 10.0)),
        
        # Metabolic/Diabetes
        'FBS': ('FASTING BLOOD SUGAR|FASTING.*GLUCOSE', 'FASTING BLOOD SUGAR(GLUCOSE)', 'mg/dl', (0.0, 500.0)),
        'HBA1C': ('HbA1c|HBA1C|GLYCATED HEMOGLOBIN', 'HbA1c', '%', (0.0, 20.0)),
        'ABG': ('AVERAGE BLOOD GLUCOSE|ABG', 'AVERAGE BLOOD GLUCOSE (ABG)', 'mg/dL', (50.0, 500.0)),
        'HOMA_IR': ('HOMA.*INSULIN RESISTANCE|HOMA.*IR', 'HOMA INSULIN RESISTANCE INDEX', 'Index', (0.0, 20.0)),
        'QUICKI': ('QUANTITATIVE INSULIN SENSITIVITY|QUICKI', 'QUANTITATIVE INSULIN SENSITIVITY INDEX', 'Index', (0.0, 1.0)),
        
        # Vitamins & Minerals
        'VITAMIN_D': ('25.*OH VITAMIN D|VITAMIN D', '25-OH VITAMIN D (TOTAL)', 'ng/mL', (0.0, 200.0)),
        'VITAMIN_B12': ('VITAMIN B.*12|B12', 'VITAMIN B-12', 'pg/mL', (0.0, 2000.0)),
        'FOLATE': ('FOLATE|FOLIC ACID|VITAMIN B9', 'FOLATE', 'ng/mL', (0.0, 50.0)),
        'VITAMIN_B9': ('VITAMIN B9|FOLIC ACID', 'VITAMIN B9/FOLIC ACID', 'ng/mL', (0.0, 50.0)),
        'FERRITIN': ('FERRITIN', 'FERRITIN', 'ng/mL', (0.0, 1000.0)),
        'IRON': ('IRON', 'IRON', 'µg/dl', (0.0, 500.0)),
        'TIBC': ('TOTAL IRON BINDING CAPACITY|TIBC', 'TOTAL IRON BINDING CAPACITY', 'µg/dL', (0.0, 1000.0)),
        'TRANSFERRIN_SATURATION': ('TRANSFERRIN SATURATION', 'TRANSFERRIN SATURATION %', '%', (0.0, 100.0)),
        'CALCIUM': ('CALCIUM', 'CALCIUM', 'mg/dL', (0.0, 20.0)),
        'MAGNESIUM': ('MAGNESIUM', 'MAGNESIUM', 'mg/dL', (0.0, 10.0)),
        'ZINC': ('SERUM ZINC|ZINC', 'SERUM ZINC', 'μg/dL', (0.0, 500.0)),
        'HOMOCYSTEINE': ('HOMOCYSTEINE', 'HOMOCYSTEINE', 'µmol/L', (0.0, 100.0)),
        
        # Electrolytes
        'SODIUM': ('SODIUM', 'SODIUM', 'mmol/L', (100.0, 200.0)),
        'POTASSIUM': ('POTASSIUM', 'POTASSIUM', 'mmol/L', (0.0, 10.0)),
        'CHLORIDE': ('CHLORIDE', 'CHLORIDE', 'mmol/L', (50.0, 150.0)),
        
        # Enzymes
        'CPK': ('CREATININE PHOSPHOKINASE|CPK|CK', 'CREATININE PHOSPHOKINASE', 'U/L', (0.0, 1000.0)),
        'LDH': ('LACTATE DEHYDROGENASE|LDH', 'LACTATE DEHYDROGENASE (LDH)', 'U/L', (0.0, 1000.0)),
        'AMYLASE': ('AMYLASE', 'AMYLASE', 'U/L', (0.0, 500.0)),
        'LIPASE': ('LIPASE', 'LIPASE', 'U/L', (0.0, 500.0)),
        
        # Inflammation
        'HS_CRP': ('HIGH SENSITIVITY C.*REACTIVE PROTEIN|HS.*CRP', 'HIGH SENSITIVITY C-REACTIVE PROTEIN (HS-CRP)', 'mg/L', (0.0, 50.0)),
        
        # Autoimmune
        'ANTI_CCP': ('ANTI CCP|ACCP', 'ANTI CCP (ACCP)', 'U/mL', (0.0, 1000.0)),
        'ANA': ('ANTI NUCLEAR ANTIBODIES|ANA', 'ANTI NUCLEAR ANTIBODIES (ANA)', 'AU/mL', (0.0, 1000.0)),
        'RF': ('RHEUMATOID FACTOR|RF', 'RHEUMATOID FACTOR (RF)', 'ng/mL', (0.0, 1000.0)),
        
        # Tumor Markers
        'PSA': ('PROSTATE SPECIFIC ANTIGEN|PSA', 'PROSTATE SPECIFIC ANTIGEN (PSA)', 'ng/mL', (0.0, 100.0)),
        'CEA': ('CARCINO EMBRYONIC ANTIGEN|CEA', 'CARCINO EMBRYONIC ANTIGEN (CEA)', 'ng/mL', (0.0, 100.0)),
        'AFP': ('ALPHA FETO PROTEIN|AFP', 'ALPHA FETO PROTEIN', 'IU/mL', (0.0, 1000.0)),
        'CA_125': ('CA 125|CA-125', 'CA 125', 'U/mL', (0.0, 1000.0)),
        'CA_19_9': ('CA 19.*9|CA-19-9', 'CA 19.9', 'U/mL', (0.0, 1000.0)),
        'CA_15_3': ('CA 15.*3|CA-15-3', 'CA 15.3', 'U/mL', (0.0, 1000.0)),
        
        # Urine Tests
        'URINE_MICROALBUMIN': ('URINARY MICROALBUMIN|MICROALBUMIN', 'URINARY MICROALBUMIN', 'μg/mL', (0.0, 1000.0)),
        'URINE_CREATININE': ('CREATININE.*URINE|URINE.*CREATININE', 'CREATININE - URINE', 'mg/dL', (0.0, 500.0)),
        'ALBUMIN_CREATININE_RATIO': ('ALBUMIN.*CREATININE RATIO|UA.*C', 'URI. ALBUMIN/CREATININE RATIO (UA/C)', 'µg/mg of Creatinine', (0.0, 1000.0)),
        'URINE_PH': ('PH|P\.H\.', 'PH', '#', None),
        'URINE_SPECIFIC_GRAVITY': ('SPECIFIC GRAVITY', 'SPECIFIC GRAVITY', '#', None),
        'URINE_GLUCOSE': ('URINARY GLUCOSE|URINE.*GLUCOSE', 'URINARY GLUCOSE', '#', None),
        'URINE_PROTEIN': ('URINARY PROTEIN|URINE.*PROTEIN', 'URINARY PROTEIN', '#', None),
        'URINE_KETONE': ('URINE KETONE|KETONE', 'URINE KETONE', '#', None),
        'URINE_BLOOD': ('URINE BLOOD|BLOOD.*URINE', 'URINE BLOOD', '#', None),
        'URINE_BILIRUBIN': ('URINARY BILIRUBIN|URINE.*BILIRUBIN', 'URINARY BILIRUBIN', '#', None),
        'UROBILINOGEN': ('UROBILINOGEN', 'UROBILINOGEN', '#', None),
        'NITRITE': ('NITRITE', 'NITRITE', '#', None),
        'LEUCOCYTE_ESTERASE': ('LEUCOCYTE ESTERASE', 'LEUCOCYTE ESTERASE', '#', None),
        'PUS_CELLS': ('URINARY LEUCOCYTES|PUS CELLS', 'URINARY LEUCOCYTES (PUS CELLS)', 'cells/HPF', None),
        'RBC_URINE': ('RED BLOOD CELLS|RBC', 'RED BLOOD CELLS', 'cells/HPF', None),
        'EPITHELIAL_CELLS': ('EPITHELIAL CELLS', 'EPITHELIAL CELLS', 'cells/HPF', None),
        'CASTS': ('CASTS', 'CASTS', '#', None),
        'CRYSTALS': ('CRYSTALS', 'CRYSTALS', '#', None),
        'BACTERIA': ('BACTERIA', 'BACTERIA', '#', None),
        'YEAST': ('YEAST', 'YEAST', '#', None),
        'MUCUS': ('MUCUS', 'MUCUS', '#', None),
        'PARASITE': ('PARASITE', 'PARASITE', '#', None),
        'BILE_PIGMENT': ('BILE PIGMENT', 'BILE PIGMENT', '#', None),
        'BILE_SALT': ('BILE SALT', 'BILE SALT', '#', None),
        
        # Other
        'ALDOSTERONE': ('ALDOSTERONE', 'ALDOSTERONE', 'ng/dL', (0.0, 100.0)),
        'EBV': ('EPSTEIN BARR.*IGG', 'EPSTEIN BARR VIRAL CAPSID ANTIGEN - IGG', 'NTU', (0.0, 10.0)),
        'HBSAG': ('HEPATITIS B SURFACE ANTIGEN|HBSAG', 'HEPATITIS B SURFACE ANTIGEN(HBSAG) RAPID TEST', '#', None),
    }
    
    def __init__(self, pdf_path):
        self.pdf_path = Path(pdf_path)
        self.text = ""
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
            return True
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return False
    
    def extract_patient_info(self):
        """Extract patient demographic information."""
        # Try multiple patterns for name extraction
        patterns = [
            r'([A-Z\s]+)\s*\((\d+)Y?\s*/\s*([MF])\)',
            r'([A-Z\s]+)\s*\((\d+)\s*Y\s*/\s*([MF])\)',
            r'Patient\s*Name\s*:?\s*([A-Z\s]+)',
            r'Name\s*:?\s*([A-Z\s]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                if len(match.groups()) == 3:
                    self.patient_info['name'] = match.group(1).strip()
                    self.patient_info['age'] = int(match.group(2))
                    self.patient_info['sex'] = 'Male' if match.group(3) == 'M' else 'Female'
                    self.patient_info['cycle'] = 'All'
                    break
                elif len(match.groups()) == 1:
                    self.patient_info['name'] = match.group(1).strip()
                    # Try to find age separately
                    age_match = re.search(r'Age\s*:?\s*(\d+)', self.text, re.IGNORECASE)
                    if age_match:
                        self.patient_info['age'] = int(age_match.group(1))
                    # Try to find sex separately
                    sex_match = re.search(r'Sex\s*:?\s*([MF]|Male|Female)', self.text, re.IGNORECASE)
                    if sex_match:
                        sex_val = sex_match.group(1).upper()
                        self.patient_info['sex'] = 'Male' if sex_val in ['M', 'MALE'] else 'Female'
                    self.patient_info['cycle'] = 'All'
                    break
    
    def find_value_for_biomarker(self, search_pattern, value_range=None):
        """Find numeric or qualitative value for a biomarker based on search pattern."""
        lines = self.text.split('\n')
        
        for i, line in enumerate(lines):
            # Check if line matches the biomarker pattern
            if re.search(search_pattern, line, re.IGNORECASE):
                # Look in current line and nearby lines
                search_lines = [line] + lines[max(0, i-2):min(len(lines), i+3)]
                
                for search_line in search_lines:
                    # First check for qualitative values (for tests like HBSAG, urine tests, etc.)
                    qualitative_patterns = [
                        r'\b(NON REACTIVE|REACTIVE|POSITIVE|NEGATIVE|ABSENT|PRESENT|NIL|TRACE)\b',
                        r'\b(DETECTED|NOT DETECTED|NORMAL|ABNORMAL)\b'
                    ]
                    
                    for qual_pattern in qualitative_patterns:
                        qual_match = re.search(qual_pattern, search_line, re.IGNORECASE)
                        if qual_match:
                            return qual_match.group(1).upper()
                    
                    # Then check for numeric patterns (including decimals)
                    matches = re.findall(r'(\d+\.?\d*)', search_line)
                    
                    for match in matches:
                        try:
                            value = float(match)
                            
                            # If value range specified, check if value is in range
                            if value_range:
                                if value_range[0] <= value <= value_range[1]:
                                    return value
                            else:
                                # For markers without range (like categorical), return if reasonable
                                if value < 1000000:  # Sanity check
                                    return value
                        except ValueError:
                            continue
        
        return None
    
    def extract_all_biomarkers(self):
        """Extract all biomarkers using standardized mapping."""
        for key, (search_pattern, standard_name, standard_unit, value_range) in self.BIOMARKER_MAP.items():
            value = self.find_value_for_biomarker(search_pattern, value_range)
            if value is not None:
                self.biomarkers[standard_name] = value
    
    def generate_json(self):
        """Generate final JSON output with patient info and biomarkers."""
        result = {**self.patient_info, **self.biomarkers}
        return result
    
    def save_json(self, output_path=None):
        """Save results to JSON file."""
        if output_path is None:
            output_path = self.pdf_path.stem + '_standardized_biomarkers.json'
        
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
        print("Usage: python standardized_extractor.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    extractor = StandardizedBiomarkerExtractor(pdf_path)
    output_file = extractor.process()
    
    if output_file:
        print(f"\nSuccess! Saved to: {output_file}")
    else:
        print("\nFailed to process PDF")
        sys.exit(1)


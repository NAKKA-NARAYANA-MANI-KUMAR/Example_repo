# Medical Lab Report Biomarker Extractor

Automatically extract biomarker values from PDF medical laboratory reports and convert to standardized JSON format.

## Features

✅ Extracts 100+ biomarker types  
✅ Standardized variable naming (AMH, DHT, FSH, etc.)  
✅ Patient demographic extraction  
✅ Clean JSON output  
✅ Reusable for multiple reports  
✅ Command-line interface  

## Installation

```bash
# Install required package
pip install PyPDF2

# Or if using virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install PyPDF2
```

## Usage

### Basic Usage

```bash
python pdf_biomarker_extractor.py your_report.pdf
```

This will:
1. Extract text from the PDF
2. Identify patient information
3. Extract all biomarkers
4. Save results to `your_report_biomarkers.json`

### Example

```bash
python pdf_biomarker_extractor.py jareena_begum.pdf
```

Output:
```
📄 Processing: jareena_begum.pdf
============================================================
✓ Extracted text from 46 pages
✓ Patient: JAREENA BEGUM, 46Y, Female

🔍 Extracting biomarkers...
  ✓ Hormones: 14
  ✓ Thyroid: 4
  ✓ Lipid Profile: 14
  ✓ Complete Blood Count: 21
  ✓ Liver/Kidney: 12
  ✓ Metabolic: 12

✓ Total biomarkers extracted: 77

💾 Saved to: jareena_begum_biomarkers.json

✅ Success! Biomarkers extracted and saved.
```

### Programmatic Usage

```python
from pdf_biomarker_extractor import BiomarkerExtractor

# Create extractor instance
extractor = BiomarkerExtractor('report.pdf')

# Process the PDF
result = extractor.process(save_output=False)

# Access data
print(f"Patient: {result['name']}")
print(f"HbA1c: {result.get('HBA', 'N/A')}")
print(f"Total Cholesterol: {result.get('TOTAL_CHOLESTEROL', 'N/A')}")
```

## Output Format

### JSON Structure

```json
{
  "name": "PATIENT NAME",
  "age": 46,
  "sex": "Female",
  "cycle": "All",
  "AMH": 0.01,
  "DHT": 462.46,
  "FBS": 87.91,
  "HBA": 5.6,
  "TOTAL_CHOLESTEROL": 271,
  ...
}
```

## Biomarker Categories

### Hormones (14)
- AMH, DHT, SHBG, 17OH, CPEP, FTES
- CORT, DHEA, PROG, E2, FSH, LH, PRL, TEST

### Thyroid (4)
- FT3, FT4, USTSH, ATG

### Lipid Profile (14)
- TOTAL_CHOLESTEROL, CHOL (HDL), LDL, TRIG, VLDL
- TC/H, TRI/H, LDL/, HD/LD, NHDL
- APOA, APOB, APB/, LPA

### Complete Blood Count (21)
- HB, PCV, RBC, MCV, MCH, MCHC
- RDWSD, RDCV, LEUC
- NEUT, LYMPH, MONO, EOS, BASO
- ANEU, ALYM, AMON, AEOS, ABAS
- PLT, MPV

### Liver Function (8)
- ALKP, BILT, BILD, GGT
- SGOT, SGPT, PROT, SALB

### Kidney Function (4)
- BUN, SCRE, EGFR, URIC

### Metabolic & Nutrition (12)
- FBS, HBA, ABG, INSFA, HOMIR
- VITDC, VITB, FOLI, FERR, IRON
- CALC, MG

## Standardized Variable Names

All biomarker variables follow the standardized naming convention:

| Variable | Full Name | Unit |
|----------|-----------|------|
| AMH | Anti-Müllerian Hormone | ng/mL |
| DHT | Dihydrotestosterone | pg/mL |
| FBS | Fasting Blood Sugar | mg/dL |
| HBA | HbA1c | % |
| LDL | LDL Cholesterol | mg/dL |
| ... | ... | ... |

See `variable_names_with_units.csv` for complete list.

## Extending the Extractor

### Add New Biomarker Category

```python
def extract_new_category(self):
    """Extract new biomarker category."""
    tests = {
        'NEW_VAR': ('Test Name in Report', 'unit', (min, max)),
    }
    
    for var_name, (test_name, unit, value_range) in tests.items():
        value = self.find_value_near_test(test_name, unit, value_range)
        if value is not None:
            self.biomarkers[var_name] = value
```

Then call it in `extract_all_biomarkers()`:
```python
self.extract_new_category()
```

## Troubleshooting

### "PyPDF2 not installed"
```bash
pip install PyPDF2
```

### "File not found"
Make sure the PDF path is correct:
```bash
python pdf_biomarker_extractor.py /full/path/to/report.pdf
```

### Fewer biomarkers than expected
The extractor uses conservative value ranges to avoid false positives. You can adjust the `value_range` parameters in the extraction methods for more aggressive extraction.

## Files

- `pdf_biomarker_extractor.py` - Main extraction script
- `variable_names_with_units.csv` - Biomarker reference table
- `ALL_MARKERS.csv` - Complete biomarker database

## Requirements

- Python 3.7+
- PyPDF2

## License

MIT License - Feel free to modify and use for your projects.

## Support

For issues or questions, please check:
1. PDF is readable and not password-protected
2. Report format is similar to Thyrocare lab reports
3. Biomarker names match expected patterns

---

**Note**: This tool is for informational purposes only. Always consult healthcare professionals for medical advice.


import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Read the JSON file
json_path = r"C:\Users\Admin\Downloads\2025-10-10-04-45-04-06d15a31-KHPMXGPTTL44.json"
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract patient information
patient_info = data.get('data', {}).get('patient_information', {})
patient_name = patient_info.get('pname', 'Unknown').replace(' ', '_').replace('.', '')
sample_code = patient_info.get('samplecode', 'Unknown')

# Create patient info rows
patient_rows = []
for key, value in patient_info.items():
    patient_rows.append({
        'Patient Info': key.replace('_', ' ').title(),
        'Data': str(value)
    })

# Create a list to store report rows
report_rows = []

# Extract the report section
report = data.get('data', {}).get('report', {})

# Process each category in the report
for category_name, category_data in report.items():
    # Skip non-dict items (like insights that might have different structure)
    if not isinstance(category_data, dict):
        continue
    
    # Check if this is actionPlan (which has a different structure)
    if category_name == 'actionPlan':
        for idx, action in enumerate(category_data):
            report_rows.append({
                'Category': 'Action Plan',
                'Subcategory': action.get('header', ''),
                'Risk Level': '',
            })
        continue
    
    # Process regular health categories
    for subcategory_name, subcategory_data in category_data.items():
        if isinstance(subcategory_data, dict):
            row = {
                'Category': category_name.replace('_', ' ').title(),
                'Subcategory': subcategory_name.replace('_', ' ').title(),
                'Risk Level': subcategory_data.get('risk_level', ''),
            }
            report_rows.append(row)
        elif subcategory_name == 'comment':
            # Handle insights comment
            report_rows.append({
                'Category': category_name.replace('_', ' ').title(),
                'Subcategory': 'Comment',
                'Risk Level': '',
            })

# Create DataFrames
df_patient = pd.DataFrame(patient_rows)
df_report = pd.DataFrame(report_rows)

# Save to Excel - Named with patient name, sample code and date time
current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f'{patient_name}_{sample_code}_{current_datetime}.xlsx'

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Write patient info section
    df_patient.to_excel(writer, sheet_name='Report', index=False, startrow=0)
    
    # Write a blank row and then report section
    start_row_report = len(df_patient) + 3  # +3 for header and blank rows
    df_report.to_excel(writer, sheet_name='Report', index=False, startrow=start_row_report)

print(f"✅ Excel file created successfully!")
print(f"   - {output_file}")
print(f"   Patient: {patient_info.get('pname', 'Unknown')}")
print(f"\nPatient info records: {len(df_patient)}")
print(f"Report records: {len(df_report)}")
print(f"Total records: {len(df_patient) + len(df_report)}")


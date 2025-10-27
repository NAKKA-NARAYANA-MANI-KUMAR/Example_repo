#!/usr/bin/env python3
"""METABOLOMICS extractor using Claude API with text extraction."""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import PyPDF2

# The METABOLOMICS extraction prompt
METABOLOMICS_PROMPT = """**Parse this medical laboratory report and convert it to standardized JSON format. Extract all available METABOLOMICS biomarkers. Return only a single JSON object with patient information and biomarker values (skip all null/missing values).**

## STANDARDIZED METABOLOMICS BIOMARKER UNITS:
- Glycine:GLYCINE : µmol/L
- Beta-AminoIsoButyric Acid:BAIBA : µmol/L
- Sarcosine:SARCOSINE : µmol/L
- Histidine:HISTIDINE : µmol/L
- MMA:MMA : µmol/L
- Uracil:URACIL : µmol/L
- Formiminoglutamate:FIGLU : µmol/L
- Serine:SERINE : µmol/L
- Carnosine:CARNOSINE : µmol/L
- beta-Alanine (Blood):B_ALANINE : µmol/L
- Threonine:THREONINE : µmol/L
- Suberate:SUBERATE : µmol/L
- GLUTAMINE (URINE):GLUTAMINE : µmol/L
- HMG2:HMG : µmol/L
- EMA:EMA : µmol/L
- PYRUVATE (URINE):PYRUVATE : µmol/L
- SUCCINATE (URINE):SUCCINATE : µmol/L
- ISOLEUCINE (URINE):ISOLEUCINE : µmol/L
- Adipate:ADIPATE : µmol/L
- Adipate:3HIV : µmol/L
- PyroGlu:PYROGLU : µmol/L
- MALATE (URINE):MALATE : µmol/L
- C0:C0 : µmol/L
- Me-succinate:ME_SUCCINATE : µmol/L
- sebacate:SEBACATE : µmol/L
- LACTATE (URINE):LACTATE : µmol/L
- 2KG:2KG : µmol/L
- 3HB:3HB : µmol/L
- Benzonate:BENZOATE : µmol/L
- 4HPA:4_HPA : µmol/L
- Indole3AA:INDOLE-3-ACETATE : µmol/L
- 3HP3HP:CLOSTRIDIAL : µmol/L
- hippurate1:HIPPURATE : µmol/L
- 4Hhippurate:4-HYDROXYHIPPURATE : µmol/L
- Taurine:TAURINE : µmol/L
- GLUTAMINE (BLOOD):GLUTAMINE_B : µmol/L
- Mandelate:MANDELATE : µmol/L
- Orotate:OROTATE : µmol/L
- Analog Cit:ANALOG_CITRATE : µmol/L
- Citrate:CITRATE : µmol/L
- Cisaconate:CIS-ACONITATE : µmol/L
- 1- Methyl-histidine:1-METHYL-HISTIDINE : µmol/L
- Cysteine:CYSTEINE : µmol/L
- Lysine:LYSINE : µmol/L
- Proline:PROLINE : µmol/L
- OXALATE (URINE):OXALATE : µmol/L
- Arginine:ARGININE : µmol/L
- Phenylalanine:PHENYLALANINE : µmol/L
- Methionine:METHIONINE : µmol/L
- Valine:VALINE : µmol/L
- Tyrosine:TYROSINE : µmol/L
- Tryptophan:TRYPTOPHAN : µmol/L
- Leucine:LEUCINE : µmol/L

## IMPORTANT EXTRACTION NOTES:
1. **Look for these specific terms** in the PDF - use the exact names as they appear in the report
2. **Search the entire document**: These values may be in different sections of the report
3. **Handle alternative names**: Look for variations in naming conventions
4. **Extract values as they appear**: No unit conversions needed
5. **IMPORTANT**: Distinguish between blood and urine samples:
   - For "beta-Alanine" - look for "beta-Alanine (Blood)" or similar blood-specific notation
   - For "GLUTAMINE" - look for "GLUTAMINE (URINE)" for urine samples
   - For "GLUTAMINE_B" - look for "GLUTAMINE (BLOOD)" for blood samples
   - For "PYRUVATE", "SUCCINATE", "ISOLEUCINE", "MALATE", "LACTATE", "OXALATE" - look for "(URINE)" notation

**IMPORTANT**: Return ONLY a valid JSON object with this structure:
{
  "name": "PATIENT NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All",
  "GLYCINE": value,
  "BAIBA": value,
  "SARCOSINE": value,
  "HISTIDINE": value,
  "MMA": value,
  "URACIL": value,
  "FIGLU": value,
  "SERINE": value,
  "CARNOSINE": value,
  "B_ALANINE": value,
  "THREONINE": value,
  "SUBERATE": value,
  "GLUTAMINE": value,
  "HMG": value,
  "EMA": value,
  "PYRUVATE": value,
  "SUCCINATE": value,
  "ISOLEUCINE": value,
  "ADIPATE": value,
  "3HIV": value,
  "PYROGLU": value,
  "MALATE": value,
  "C0": value,
  "ME_SUCCINATE": value,
  "SEBACATE": value,
  "LACTATE": value,
  "2KG": value,
  "3HB": value,
  "BENZOATE": value,
  "4_HPA": value,
  "INDOLE-3-ACETATE": value,
  "CLOSTRIDIAL": value,
  "HIPPURATE": value,
  "4-HYDROXYHIPPURATE": value,
  "TAURINE": value,
  "GLUTAMINE_B": value,
  "MANDELATE": value,
  "OROTATE": value,
  "ANALOG_CITRATE": value,
  "CITRATE": value,
  "CIS-ACONITATE": value,
  "1-METHYL-HISTIDINE": value,
  "CYSTEINE": value,
  "LYSINE": value,
  "PROLINE": value,
  "OXALATE": value,
  "ARGININE": value,
  "PHENYLALANINE": value,
  "METHIONINE": value,
  "VALINE": value,
  "TYROSINE": value,
  "TRYPTOPHAN": value,
  "LEUCINE": value
}

Extract patient name, age, and sex from the report. Use "Male" or "Female" for sex."""


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file."""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text


def process_pdf_with_claude(pdf_path: str, api_key: str) -> dict | None:
    """Process PDF and extract METABOLOMICS data."""
    try:
        print(f"Extracting text from PDF...")
        text = extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            print("Error: Could not extract text from PDF")
            return None
        
        print(f"Extracted {len(text)} characters")
        print(f"Sending to Claude API...")
        
        # Initialize client
        client = anthropic.Anthropic(api_key=api_key)
        
        # Create message
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": f"{METABOLOMICS_PROMPT}\n\n---REPORT TEXT---\n{text}"
                }
            ]
        )
        
        # Extract JSON from response
        response_text = message.content[0].text.strip()
        print(f"Response received: {response_text[:200]}...")
        
        # Parse JSON
        json_text = None
        
        # Try to find JSON in code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end > json_start:
                json_text = response_text[json_start:json_end].strip()
        
        # Try to find JSON object
        if not json_text:
            first_brace = response_text.find("{")
            last_brace = response_text.rfind("}")
            if first_brace >= 0 and last_brace > first_brace:
                json_text = response_text[first_brace:last_brace + 1]
        
        if not json_text:
            print("Error: Could not extract JSON from response")
            print(f"Full response: {response_text}")
            return None
        
        result = json.loads(json_text)
        
        # Add default values if missing
        if "cycle" not in result:
            result["cycle"] = "All"
        
        print(f"✓ Successfully extracted data")
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Extract METABOLOMICS data from PDF")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("-o", "--output", help="Output JSON file path", default=None)
    parser.add_argument("--api-key", help="Anthropic API key", default=None)
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    # Set output path
    output_path = args.output or Path(args.pdf_path).with_suffix('.json')
    
    print(f"Processing: {args.pdf_path}")
    print(f"Output: {output_path}")
    print("-" * 50)
    
    # Process PDF
    result = process_pdf_with_claude(args.pdf_path, api_key)
    
    if result:
        # Save result
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print("\n" + "="*50)
        print("SUCCESS!")
        print("="*50)
        print(f"Output saved to: {output_path}")
        print(f"\nPatient: {result.get('name', 'Unknown')}")
        print(f"Age: {result.get('age', 'Unknown')}")
        print(f"Sex: {result.get('sex', 'Unknown')}")
        
        biomarkers = {k: v for k, v in result.items() if k not in ["name", "age", "sex", "cycle"]}
        if biomarkers:
            print(f"\nExtracted {len(biomarkers)} METABOLOMICS biomarkers:")
            for key, value in biomarkers.items():
                print(f"  {key}: {value}")
    else:
        print("\n" + "="*50)
        print("FAILED!")
        print("="*50)
        sys.exit(1)


if __name__ == "__main__":
    main()

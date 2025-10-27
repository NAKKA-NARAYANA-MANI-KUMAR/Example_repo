#!/usr/bin/env python3
"""LIPOMICS extractor using Claude API with text extraction."""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import PyPDF2

# The LIPOMICS extraction prompt
LIPOMICS_PROMPT = """**Parse this medical laboratory report and convert it to standardized JSON format. Extract all available LIPOMICS biomarkers. Return only a single JSON object with patient information and biomarker values (skip all null/missing values).**

## STANDARDIZED LIPOMICS BIOMARKER UNITS:
- Polyunsaturated Omega-3 Fatty Acids:PUFA_O3 : %
- Polyunsaturated Omega-6 Fatty Acids:PUFA_O6 : %
- cis-Monounsaturated Fatty Acids:MUFA : %
- Saturated Fatty Acids:SFA : %
- Trans Fatty Acids:TFA : %
- Omega-3 Index:O3_INDEX : %
- Omega-6/Omega3 Ratio:O6_O3_RATIO : Ratio
- Palmitic Acid Index:PALM_INDEX : %
- AA/EPA Ratio:AA_EPA_RATIO : Ratio
- Trans Fat Index (TFI):TFI : %

## IMPORTANT EXTRACTION NOTES:
1. **Look for these specific terms** in the PDF:
   - "Polyunsaturated Omega-3 Fatty Acids"
   - "Polyunsaturated Omega-6 Fatty Acids"
   - "cis-Monounsaturated Fatty Acids"
   - "Saturated Fatty Acids"
   - "Trans Fatty Acids"
   - "Omega-3 Index"
   - "Omega-6/Omega3 Ratio" or "Omega-6/Omega-3 Ratio"
   - "Palmitic Acid Index"
   - "AA/EPA Ratio"
   - "Trans Fat Index (TFI)" or "TFI"
2. **Search the entire document**: These values may be in different sections of the report.
3. **Handle alternative names**: Look for variations in naming conventions.
4. **Extract values as they appear**: No unit conversions needed.

**IMPORTANT**: Return ONLY a valid JSON object with this structure:
{
  "name": "PATIENT NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All",
  "PUFA_O3": value,
  "PUFA_O6": value,
  "MUFA": value,
  "SFA": value,
  "TFA": value,
  "O3_INDEX": value,
  "O6_O3_RATIO": value,
  "PALM_INDEX": value,
  "AA_EPA_RATIO": value,
  "TFI": value
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
    """Process PDF and extract LIPOMICS data."""
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
                    "content": f"{LIPOMICS_PROMPT}\n\n---REPORT TEXT---\n{text}"
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
    parser = argparse.ArgumentParser(description="Extract LIPOMICS data from PDF")
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
            print(f"\nExtracted {len(biomarkers)} LIPOMICS biomarkers:")
            for key, value in biomarkers.items():
                print(f"  {key}: {value}")
    else:
        print("\n" + "="*50)
        print("FAILED!")
        print("="*50)
        sys.exit(1)


if __name__ == "__main__":
    main()

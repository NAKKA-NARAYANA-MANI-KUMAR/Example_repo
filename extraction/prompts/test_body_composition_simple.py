#!/usr/bin/env python3
"""Simple body composition extractor using Claude API with text extraction."""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import PyPDF2

# The body composition extraction prompt
BODY_COMPOSITION_PROMPT = """**Parse this medical laboratory report and convert it to standardized JSON format. Extract all available body composition biomarkers. Return only a single JSON object with patient information and biomarker values (skip all null/missing values).**

## STANDARDIZED BODY COMPOSITION BIOMARKER UNITS:
- TotalFAT(%):TOTAL_BODY_FAT_PERCENTAGE : %
- Total Bone Mass:TOTAL_BONE_MASS : kg
- Total Soft Tissue:TOTAL_SOFT_TISSUE : kg
- Total Lean Mass:TOTAL_LEAN_MASS : kg
- VAT Mass (g):VAT_MASS : g
- SAT/VAT Ratio:SAT_VAT_RATIO : Ratio
- VAT Area (㎠):VAT_AREA : cm²
- ASM/Height^2:ASM_HEIGHT_SQUARED : kg/m²
- ASM/Weight:ASM_WEIGHT : Ratio
- ASM/BMI:ASM_BMI : Ratio
- A/G Ratio:A_G_RATIO : Ratio
- T-Score:T_SCORE : Score
- Z-Score:Z_SCORE : Score
- Body Weight:BODY_WEIGHT : kg

## IMPORTANT EXTRACTION NOTES:
1. **Body Weight**: Look for "Body Weight" in the "Total Body Composition" table, NOT the "Weight" from "Measurement Results" section. The correct Body Weight is in the Total Body Composition table (usually around 62.1, not 63.3).
2. **T-Score and Z-Score**: These are typically found at the bottom of bone density tables in the "Total" row, not for individual body regions.
3. **Search the entire document**: Some values like Body Weight may be in different sections of the report.
4. **Look for alternative names**: Body Weight might appear as "Body Weight" in composition tables, not just "Weight" from measurement results.
5. **PRIORITY**: Use the Body Weight from "Total Body Composition" section, not from "Measurement Results" section.

**IMPORTANT**: Return ONLY a valid JSON object with this structure:
{
  "name": "PATIENT NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All",
  "TOTAL_BODY_FAT_PERCENTAGE": value,
  ...other biomarkers found...
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
    """Process PDF and extract body composition data."""
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
                    "content": f"{BODY_COMPOSITION_PROMPT}\n\n---REPORT TEXT---\n{text}"
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
    parser = argparse.ArgumentParser(description="Extract body composition data from PDF")
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
            print(f"\nExtracted {len(biomarkers)} biomarkers:")
            for key, value in biomarkers.items():
                print(f"  {key}: {value}")
    else:
        print("\n" + "="*50)
        print("FAILED!")
        print("="*50)
        sys.exit(1)


if __name__ == "__main__":
    main()


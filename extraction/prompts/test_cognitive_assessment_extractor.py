#!/usr/bin/env python3
"""COGNITIVE ASSESSMENT extractor using Claude API with text extraction."""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import PyPDF2

# The COGNITIVE ASSESSMENT extraction prompt
COGNITIVE_ASSESSMENT_PROMPT = """**Parse this medical laboratory report and convert it to standardized JSON format. Extract all available COGNITIVE ASSESSMENT biomarkers. Return only a single JSON object with patient information and biomarker values (include all keys even if empty).**

## STANDARDIZED COGNITIVE ASSESSMENT BIOMARKER UNITS:
- Overall Brain Score:OVERALL_BRAIN_SCORE : score
- Attention:ATTENTION : score
- Immediate Memory:IMMEDIATE_MEMORY : score
- Working Memory:WORKING_MEMORY : score
- Brain Executive Function:BRAIN_EXECUTIVE_FUNCTION : score

## IMPORTANT EXTRACTION NOTES:
1. **Include ALL keys** - even if values are empty, include the key with null/empty value
2. **Extract exact values** as they appear in the report
3. **For scores** - extract the numerical values
4. **Search the entire document**: These values may be in different sections of the report
5. **Use "Male" or "Female"** for sex (never abbreviations)
6. **Include patient demographics** (name, age, sex, cycle)

**IMPORTANT**: Return ONLY a valid JSON object with this structure:
{
  "name": "PATIENT NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All",
  "OVERALL_BRAIN_SCORE": value,
  "ATTENTION": value,
  "IMMEDIATE_MEMORY": value,
  "WORKING_MEMORY": value,
  "BRAIN_EXECUTIVE_FUNCTION": value
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
    """Process PDF and extract COGNITIVE ASSESSMENT data."""
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
                    "content": f"{COGNITIVE_ASSESSMENT_PROMPT}\n\n---REPORT TEXT---\n{text}"
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
    parser = argparse.ArgumentParser(description="Extract COGNITIVE ASSESSMENT data from PDF")
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
            print(f"\nExtracted {len(biomarkers)} COGNITIVE ASSESSMENT biomarkers:")
            for key, value in biomarkers.items():
                print(f"  {key}: {value}")
    else:
        print("\n" + "="*50)
        print("FAILED!")
        print("="*50)
        sys.exit(1)


if __name__ == "__main__":
    main()

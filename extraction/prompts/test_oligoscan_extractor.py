#!/usr/bin/env python3
"""OLIGOSCAN extractor using Claude API with text extraction."""

import argparse
import json
import os
import sys
from pathlib import Path

import anthropic
import PyPDF2

# The OLIGOSCAN extraction prompt
OLIGOSCAN_PROMPT = """**Parse this medical laboratory report and convert it to standardized JSON format. Extract all available OLIGOSCAN biomarkers. Return only a single JSON object with patient information and biomarker values (include all keys even if empty).**

## STANDARDIZED OLIGOSCAN BIOMARKER UNITS:
# Heavy Metals
- Aluminium (Al):ALUMINIUM : %
- Antimony (Sb):ANTIMONY : %
- Silver (Ag):SILVER : %
- Arsenic (As):ARSENIC : %
- Barium (Ba):BARIUM : %
- Beryllium (Be):BERYLLIUM : %
- Bismuth (Bi):BISMUTH : %
- Cadmium (Cd):CADMIUM : %
- Mercury (Hg):MERCURY : %
- Nickel (Ni):NICKEL : %
- Platinum (Pt):PLATINUM : %
- Lead (Pb):LEAD : %
- Thallium (Tl):THALLIUM : %
- Thorium (Th):THORIUM : %
- Gadolinium (Gd):GADOLINIUM : %

# Vitamins
- Vitamin A:VITAMIN_A : %
- Vitamin C:VITAMIN_C : %
- Vitamin E:VITAMIN_E : %
- Vitamin B6:VITAMIN_B6 : %
- Vitamin B12:VITAMIN_B12 : %
- Vitamin D:VITAMIN_D3 : %
- Folic acid (B9):FOLIC_ACID : %

# Minerals
- CALCIUM (Ca):CALCIUM : %
- MAGNESIUM (Mg):MAGNESIUM : %
- PHOSPHORUS (P):PHOSPHORUS : %
- SILICON (Si):SILICON : %
- SODIUM (Na):SODIUM : %
- POTASSIUM (K):POTASSIUM : %
- COPPER (Cu):COPPER : %
- ZINC (Zn):ZINC : %
- CHROMIUM (Cr):CHROMIUM : %
- IODINE (I):IODINE : %
- SELENIUM (Se):SELENIUM : %
- SULPHUR (S):SULPHUR : %
- IRON (Fe):IRON : %
- MANGANESE (Mn):MANGANESE : %
- VANADIUM (V):VANADIUM : %
- BORON (B):BORON : %
- COBALT (Co):COBALT : %
- MOLYBDENUM (Mo):MOLYBDENUM : %
- LITHIUM (Li):LITHIUM : %
- GERMANIUM (Ge):GERMANIUM : %
- FLUOR (F):FLUOR : %

# Ratios
- CA/MG:CA/MG : %
- CA/P:CA/P : %
- K/NA:K/NA : %
- CU/ZN:CU/ZN : %

# Ratio Excess/Deficiency Flags (extract element names that appear in deficiency/excess columns)
- CA/MG_EXCESS:CA/MG_EXCESS : text
- CA/P_EXCESS:CA/P_EXCESS : text
- K/NA_EXCESS:K/NA_EXCESS : text
- CU/ZN_EXCESS:CU/ZN_EXCESS : text
- CA/MG_DEFICIENCY:CA/MG_DEFICIENCY : text
- CA/P_DEFICIENCY:CA/P_DEFICIENCY : text
- K/NA_DEFICIENCY:K/NA_DEFICIENCY : text
- CU/ZN_DEFICIENCY:CU/ZN_DEFICIENCY : text

# Oxidative Stress
- Oxidative Aggression:OXIDATIVE_AGGREGATION_SCORE : score
- Oxidative Aggression Range:OXIDATIVE_AGGREGATION_RANGE : text
- Antioxidant Protection:ANTIOXIDANT_PROTECTION_SCORE : score
- Antioxidant Protection Range:ANTIOXIDANT_PROTECTION_RANGE : text

# Anti-Aging Skin
- Elasticity - Texture:ELASTICITY_TEXTURE_SCORE : score
- Elasticity - Texture Range:ELASTICITY_TEXTURE_RANGE : text
- Aging Condition:AGING_CONDITION_SCORE : score
- Aging Condition Range:AGING_CONDITION_RANGE : text
- Fragility:FRAGILITY_SCORE : score
- Fragility Range:FRAGILITY_RANGE : text

# Slimness
- Fat excess:FAT_EXCESS_SCORE : score
- Fat excess Range:FAT_EXCESS_RANGE : text
- Aqueous tendency:AQUEOUS_TENDENCY_SCORE : %
- Adipose tendency:ADIPOSE_TENDENCY_SCORE : %
- Fibrous tendency:FIBROUS_TENDENCY_SCORE : %

# Hair/Nails
- Falling tendency:FALLING_TENDENCY_SCORE : score
- Falling tendency Range:FALLING_TENDENCY_RANGE : text
- Quality:QUALITY_SCORE : score
- Quality Range:QUALITY_RANGE : text

# Joints
- Flexibility:FLEXIBILITY_SCORE : score
- Flexibility Range:FLEXIBILITY_RANGE : text
- Acid-base balance:ACID_BASE_BALANCE_SCORE : score
- Acid-base balance Range:ACID_BASE_BALANCE_RANGE : text
- Tissue Repair:TISSUE_REPAIR_SCORE : score
- Tissue Repair Range:TISSUE_REPAIR_RANGE : text

# Detox
- Sulfoconjugation Index:SULFOCONJUGATION_INDEX_SCORE : score
- Sulfoconjugation Index Range:SULFOCONJUGATION_INDEX_RANGE : text
- Overall Intoxication:OVERALL_INTOXICATION_SCORE : score
- Overall Intoxication Range:OVERALL_INTOXICATION_RANGE : text
- Metabolic Overload:METABOLIC_OVERLOAD_SCORE : score
- Metabolic Overload Range:METABOLIC_OVERLOAD_RANGE : text

# Digestion
- Trace Mineral Assimilation:TRACE_MINERAL_ASSIMILATION_SCORE : score
- Trace Mineral Assimilation Range:TRACE_MINERAL_ASSIMILATION_RANGE : text
- Enzymatic Balance:ENZYMATIC_BALANCE_SCORE : score
- Enzymatic Balance Range:ENZYMATIC_BALANCE_RANGE : text
- Glycemic Balance:GLYCEMIC_BALANCE_SCORE : score
- Glycemic Balance Range:GLYCEMIC_BALANCE_RANGE : text

# Mental Condition
- Cognitive Function:COGNITIVE_FUNCTION_SCORE : score
- Cognitive Function Range:COGNITIVE_FUNCTION_RANGE : text
- Emotional Balance:EMOTIONAL_BALANCE_SCORE : score
- Emotional Balance Range:EMOTIONAL_BALANCE_RANGE : text
- Nervous System:NERVOUS_SYSTEM_SCORE : score
- Nervous System Range:NERVOUS_SYSTEM_RANGE : text

# General Balance
- Natural Defenses:NATURAL_DEFENSES_SCORE : score
- Natural Defenses Range:NATURAL_DEFENSES_RANGE : text
- Hormonal Balance:HORMONAL_BALANCE_SCORE : score
- Hormonal Balance Range:HORMONAL_BALANCE_RANGE : text
- Cardiovascular:CARDIOVASCULAR_SCORE : score
- Cardiovascular Range:CARDIOVASCULAR_RANGE : text
- Predisposition for Allergies:PREDISPOSITION_FOR_ALLERGIES_SCORE : score
- Predisposition for Allergies Range:PREDISPOSITION_FOR_ALLERGIES_RANGE : text

## IMPORTANT EXTRACTION NOTES:
1. **Include ALL keys** - even if values are empty, include the key with null/empty value
2. **Extract exact values** as they appear in the report
3. **For ratio values** (CA/MG, CA/P, K/NA, CU/ZN) - extract the actual percentage values from the report
4. **For deficiency/excess flags** - CRITICAL: Look for actual deficiency/excess columns in the report. If these columns are empty/blank, return empty string "". DO NOT infer values from ratio names (e.g., don't put "Ca Mg" for CA/MG just because the ratio name contains Ca and Mg). Only extract what is explicitly written in the deficiency/excess columns of the report.
5. **For ranges** - extract the text assessment (good, acceptable, bad, to correct, etc.)
6. **For scores** - extract the numerical values
7. **For percentages** - extract the percentage values
8. **Search the entire document**: These values may be in different sections of the report

## CRITICAL RULE FOR DEFICIENCY/EXCESS FLAGS:
- If the deficiency column for CA/MG is empty → CA/MG_DEFICIENCY: ""
- If the excess column for CA/MG is empty → CA/MG_EXCESS: ""
- DO NOT put "Ca Mg" just because the ratio is called "CA/MG"
- ONLY extract what is actually written in the deficiency/excess columns
- If columns are blank/empty, return empty string ""

**IMPORTANT**: Return ONLY a valid JSON object with this structure:
{
  "name": "PATIENT NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All",
  "ALUMINIUM": value,
  "ANTIMONY": value,
  "SILVER": value,
  "ARSENIC": value,
  "BARIUM": value,
  "BERYLLIUM": value,
  "BISMUTH": value,
  "CADMIUM": value,
  "MERCURY": value,
  "NICKEL": value,
  "PLATINUM": value,
  "LEAD": value,
  "THALLIUM": value,
  "THORIUM": value,
  "GADOLINIUM": value,
  "VITAMIN_A": value,
  "VITAMIN_C": value,
  "VITAMIN_E": value,
  "VITAMIN_B6": value,
  "VITAMIN_B12": value,
  "VITAMIN_D3": value,
  "FOLIC_ACID": value,
  "CALCIUM": value,
  "MAGNESIUM": value,
  "PHOSPHORUS": value,
  "SILICON": value,
  "SODIUM": value,
  "POTASSIUM": value,
  "COPPER": value,
  "ZINC": value,
  "CHROMIUM": value,
  "IODINE": value,
  "SELENIUM": value,
  "SULPHUR": value,
  "IRON": value,
  "MANGANESE": value,
  "VANADIUM": value,
  "BORON": value,
  "COBALT": value,
  "MOLYBDENUM": value,
  "LITHIUM": value,
  "GERMANIUM": value,
  "FLUOR": value,
  "CA/MG": value,
  "CA/P": value,
  "K/NA": value,
  "CU/ZN": value,
  "CA/MG_EXCESS": value,
  "CA/P_EXCESS": value,
  "K/NA_EXCESS": value,
  "CU/ZN_EXCESS": value,
  "CA/MG_DEFICIENCY": value,
  "CA/P_DEFICIENCY": value,
  "K/NA_DEFICIENCY": value,
  "CU/ZN_DEFICIENCY": value,
  "OXIDATIVE_AGGREGATION_SCORE": value,
  "OXIDATIVE_AGGREGATION_RANGE": value,
  "ANTIOXIDANT_PROTECTION_SCORE": value,
  "ANTIOXIDANT_PROTECTION_RANGE": value,
  "ELASTICITY_TEXTURE_SCORE": value,
  "ELASTICITY_TEXTURE_RANGE": value,
  "AGING_CONDITION_SCORE": value,
  "AGING_CONDITION_RANGE": value,
  "FRAGILITY_SCORE": value,
  "FRAGILITY_RANGE": value,
  "FAT_EXCESS_SCORE": value,
  "FAT_EXCESS_RANGE": value,
  "AQUEOUS_TENDENCY_SCORE": value,
  "ADIPOSE_TENDENCY_SCORE": value,
  "FIBROUS_TENDENCY_SCORE": value,
  "FALLING_TENDENCY_SCORE": value,
  "FALLING_TENDENCY_RANGE": value,
  "QUALITY_SCORE": value,
  "QUALITY_RANGE": value,
  "FLEXIBILITY_SCORE": value,
  "FLEXIBILITY_RANGE": value,
  "ACID_BASE_BALANCE_SCORE": value,
  "ACID_BASE_BALANCE_RANGE": value,
  "TISSUE_REPAIR_SCORE": value,
  "TISSUE_REPAIR_RANGE": value,
  "SULFOCONJUGATION_INDEX_SCORE": value,
  "SULFOCONJUGATION_INDEX_RANGE": value,
  "OVERALL_INTOXICATION_SCORE": value,
  "OVERALL_INTOXICATION_RANGE": value,
  "METABOLIC_OVERLOAD_SCORE": value,
  "METABOLIC_OVERLOAD_RANGE": value,
  "TRACE_MINERAL_ASSIMILATION_SCORE": value,
  "TRACE_MINERAL_ASSIMILATION_RANGE": value,
  "ENZYMATIC_BALANCE_SCORE": value,
  "ENZYMATIC_BALANCE_RANGE": value,
  "GLYCEMIC_BALANCE_SCORE": value,
  "GLYCEMIC_BALANCE_RANGE": value,
  "COGNITIVE_FUNCTION_SCORE": value,
  "COGNITIVE_FUNCTION_RANGE": value,
  "EMOTIONAL_BALANCE_SCORE": value,
  "EMOTIONAL_BALANCE_RANGE": value,
  "NERVOUS_SYSTEM_SCORE": value,
  "NERVOUS_SYSTEM_RANGE": value,
  "NATURAL_DEFENSES_SCORE": value,
  "NATURAL_DEFENSES_RANGE": value,
  "HORMONAL_BALANCE_SCORE": value,
  "HORMONAL_BALANCE_RANGE": value,
  "CARDIOVASCULAR_SCORE": value,
  "CARDIOVASCULAR_RANGE": value,
  "PREDISPOSITION_FOR_ALLERGIES_SCORE": value,
  "PREDISPOSITION_FOR_ALLERGIES_RANGE": value
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
    """Process PDF and extract OLIGOSCAN data."""
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
                    "content": f"{OLIGOSCAN_PROMPT}\n\n---REPORT TEXT---\n{text}"
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
    parser = argparse.ArgumentParser(description="Extract OLIGOSCAN data from PDF")
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
            print(f"\nExtracted {len(biomarkers)} OLIGOSCAN biomarkers:")
            for key, value in biomarkers.items():
                print(f"  {key}: {value}")
    else:
        print("\n" + "="*50)
        print("FAILED!")
        print("="*50)
        sys.exit(1)


if __name__ == "__main__":
    main()

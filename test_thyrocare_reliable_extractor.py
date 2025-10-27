#!/usr/bin/env python3
"""Extract Thyrocare data using reliable approach with better error handling."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import anthropic
import pdfplumber

# Reliable prompt for consistent extraction
RELIABLE_PROMPT = """**Extract ALL Thyrocare biomarkers from this medical report. Return JSON with patient info and ALL biomarker values found.**

## PATIENT INFO:
```json
{
  "name": "PATIENT FULL NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All"
}
```

## EXTRACT ALL THESE BIOMARKERS:
**Hormones**: AMH, DHT, SHBG, FTES, E2, PROG, FSH, LH, PRL, TEST, CORT, DHEA, ACTH, INGF1
**Thyroid**: FT3, FT4, USTSH, ANTI_TPO, ATG
**Liver**: SGPT, SGOT, ALKP, GGT, BILT, BILD, BILI, PROT, SALB, A/GR
**Kidney**: SCRE, BUN, EGFR, URIC, CALC, CHL, POT, SOD, MG
**Lipids**: CHOL, TRIG, HCHO, LDL, VLDL, APOA, APOB, LPA
**Blood**: HB, PCV, RBC, WBC, PLT, NEUT, LYMPH, MONO, EOS, BASO
**Tumor Markers**: CEA, AFP, PSA, C199, CALCT
**Vitamins**: VITDC, VITB, VITB9, FERR, IRON
**Inflammation**: HSCRP, RFAC, ANA, ACCP
**Urine Tests**: UBACT, UCAST, UCRYS, ULEST, UMUC, UNIT, UPAR, UBIL, UGLU, UPROT, UBLD, UKET, UBNGN, UYST, UBPIG, UBSAL

## CRITICAL RULES:
1. Extract patient demographics (name, age, sex)
2. Look for urine test sections with "ABSENT" or "PRESENT" values
3. Include "ABSENT" values for urine tests, don't skip them
4. Extract calculated ratios when available
5. Use exact biomarker names as they appear in the report
6. **SEARCH THE ENTIRE DOCUMENT** - biomarkers may be in different sections

**Return JSON with patient info and ALL biomarkers found.**"""

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def split_text_into_chunks(text: str, chunk_size: int = 35000) -> list[str]:
    """Split text into chunks with better overlap."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at a reasonable point
        if end < len(text):
            break_point = end
            for i in range(min(1000, chunk_size // 10)):
                if text[end - i] in ['\n', '.', ' ']:
                    break_point = end - i
                    break
            end = break_point
        
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - 4000  # Larger overlap for better coverage
        
    return chunks

def process_chunk_with_claude(chunk: str, api_key: str, chunk_num: int, total_chunks: int, max_retries: int = 5) -> dict | None:
    """Process a single chunk with Claude API with robust retry logic."""
    for attempt in range(max_retries):
        try:
            print(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} chars)... (attempt {attempt + 1}/{max_retries})")
            
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
                        "content": f"{RELIABLE_PROMPT}\n\n---REPORT TEXT CHUNK {chunk_num}---\n{chunk}"
                    }
                ]
            )
            
            # Extract JSON from response
            response_text = message.content[0].text.strip()
            
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
                print(f"Warning: Could not extract JSON from chunk {chunk_num}")
                return None
            
            result = json.loads(json_text)
            print(f"✓ Chunk {chunk_num} processed successfully")
            return result
            
        except anthropic.RateLimitError as e:
            wait_time = (2 ** attempt) * 30  # Exponential backoff: 30s, 60s, 120s, 240s, 480s
            print(f"Rate limit hit on chunk {chunk_num}. Waiting {wait_time} seconds before retry...")
            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            else:
                print(f"Max retries reached for chunk {chunk_num}. Rate limit still active.")
                return None
                
        except Exception as e:
            print(f"Error processing chunk {chunk_num} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 20  # Wait 20 seconds before retry
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                return None
    
    return None

def merge_results(results: list[dict]) -> dict:
    """Merge results from multiple chunks with better conflict resolution."""
    if not results:
        return {}
    
    merged = {
        "name": "Unknown",
        "age": None,
        "sex": "Unknown",
        "cycle": "All"
    }
    
    for result in results:
        # Extract patient info (use first non-unknown value)
        if "name" in result and result["name"] != "Unknown":
            merged["name"] = result["name"]
        if "age" in result and result["age"] is not None:
            merged["age"] = result["age"]
        if "sex" in result and result["sex"] != "Unknown":
            merged["sex"] = result["sex"]
        
        # Merge biomarkers (prefer non-null values)
        for key, value in result.items():
            if key not in ["name", "age", "sex", "cycle"] and value is not None:
                # If key already exists, prefer non-null values
                if key not in merged or merged[key] is None:
                    merged[key] = value
    
    return merged

def process_pdf_reliable(pdf_path: str, api_key: str) -> dict | None:
    """Process PDF using reliable approach with better error handling."""
    print(f"Extracting text from PDF...")
    full_text = extract_text_from_pdf(pdf_path)
    
    if not full_text.strip():
        print("Error: Could not extract text from PDF")
        return None
    
    print(f"Extracted {len(full_text)} characters")
    
    chunks = split_text_into_chunks(full_text, 35000)
    print(f"Split into {len(chunks)} chunks")
    
    results = []
    
    for i, chunk in enumerate(chunks, 1):
        # Delay between requests to avoid rate limits
        if i > 1:
            print("Waiting 25 seconds to avoid rate limits...")
            time.sleep(25)
        
        result = process_chunk_with_claude(chunk, api_key, i, len(chunks))
        if result:
            results.append(result)
    
    if not results:
        print("No data extracted from any chunk.")
        return None
    
    print(f"✓ Successfully processed {len(results)} chunks")
    return merge_results(results)

def main():
    parser = argparse.ArgumentParser(description="Extract Thyrocare data using reliable approach.")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("-o", "--output", help="Output JSON file path", default=None)
    parser.add_argument("--api-key", help="Anthropic API key", default=None)
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    output_path = args.output or str(Path(args.pdf_path).with_suffix('')) + '_reliable.json'
    
    print(f"Processing: {args.pdf_path}")
    print(f"Output: {output_path}")
    print("-" * 50)
    
    start_time = time.time()
    result = process_pdf_reliable(args.pdf_path, api_key)
    end_time = time.time()
    
    if result:
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print("\n" + "="*50)
        print("SUCCESS!")
        print("="*50)
        print(f"Output saved to: {output_path}")
        print(f"Processing time: {end_time - start_time:.2f} seconds")
        print(f"\nPatient: {result.get('name', 'Unknown')}")
        print(f"Age: {result.get('age', 'Unknown')}")
        print(f"Sex: {result.get('sex', 'Unknown')}")
        
        biomarkers = {k: v for k, v in result.items() if k not in ["name", "age", "sex", "cycle"]}
        if biomarkers:
            print(f"\nExtracted {len(biomarkers)} Thyrocare biomarkers:")
            for key, value in biomarkers.items():
                print(f"  {key}: {value}")
    else:
        print("\n" + "="*50)
        print("FAILED!")
        print("="*50)
        sys.exit(1)

if __name__ == "__main__":
    main()


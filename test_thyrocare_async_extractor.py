#!/usr/bin/env python3
"""Extract Thyrocare data using asynchronous processing for faster extraction."""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import anthropic
import pdfplumber

# Full Thyrocare prompt for async processing
ASYNC_PROMPT = """**Parse this medical laboratory report and convert it to standardized JSON format. Extract all available biomarkers and convert them to the specified units below. Return only a single JSON object with patient information and biomarker values (skip all null/missing values).**

## PATIENT INFO FORMAT:
```json
{
  "name": "PATIENT FULL NAME",
  "age": number,
  "sex": "Male" or "Female",
  "cycle": "All"
}
```

## STANDARDIZED BIOMARKER UNITS:
17 OH PROGESTERONE:17OH : ng/mL
25-OH VITAMIN D (TOTAL):VITDC : ng/mL
ADRENOCORTICOTROPIC HORMONE (ACTH):ACTH : pg/mL
ALANINE TRANSAMINASE (SGPT):SGPT : U/L
ALBUMIN - SERUM:SALB : gm/dL
ALDOSTERONE:ALDOS : ng/dL
ALKALINE PHOSPHATASE:ALKP : U/L
ALPHA FETO PROTEIN:AFP : IU/mL
AMYLASE:AMYL : U/L
ANTI CCP (ACCP):ACCP : U/mL
ANTI MICROSOMAL ANTIBODY (AMA):AMA : IU/mL
ANTI MULLERIAN HORMONE (AMH):AMH : ng/mL
ANTI NUCLEAR ANTIBODIES (ANA):ANA : AU/mL
ANTI THYROGLOBULIN ANTIBODY (ATG):ATG : IU/ml
ANTI-THYROID PEROXIDASE ANTIBODIES:ANTI_TPO : IU/mL
APO B / APO A1 RATIO (APO B/A1):APB/ : Ratio
APOLIPOPROTEIN - A1 (APO-A1):APOA : mg/dL
APOLIPOPROTEIN - B (APO-B):APOB : mg/dL
ASPARTATE AMINOTRANSFERASE (SGOT ):SGOT : U/L
AVERAGE BLOOD GLUCOSE (ABG):ABG : mg/dL
BACTERIA:UBACT : # (PRESENT/ABSENT)
BASOPHILS - ABSOLUTE COUNT:ABAS : X 10³ / µL
BASOPHILS PERCENTAGE:BASO : %
BETA HCG:BHCG : mIU/mL
BILE PIGMENT:UBPIG : # (PRESENT/ABSENT)
BILE SALT:UBSAL : # (PRESENT/ABSENT)
BILIRUBIN (INDIRECT):BILI : mg/dL
BILIRUBIN - DIRECT:BILD : mg/dL
BILIRUBIN - TOTAL:BILT : mg/dL
BLOOD UREA NITROGEN (BUN):BUN : mg/dL
BUN / Sr.CREATININE RATIO:B/CR : Ratio
C-PEPTIDE:CPEP : ng/mL
CA 125:C125 : U/mL
CA 15.3:C153 : U/mL
CA 19.9:C199 : U/mL
CALCITONIN:CALCT : pg/mL
CALCIUM:CALC : mg/dL
CARCINO EMBRYONIC ANTIGEN (CEA):CEA : ng/mL
CASTS:UCAST : # (PRESENT/ABSENT)
CHLORIDE:CHL : mmol/L
CORTISOL:CORT : µg/dl
CREATININE - SERUM:SCRE : mg/dL
CREATININE - URINE:UCRA : mg/dL
CREATININE PHOSPHOKINASE:CPK : U/L
CRYSTALS:UCRYS : # (PRESENT/ABSENT)
CYSTATIN C:CYST : mg/L
DHEA - SULPHATE (DHEAS):DHEA : μg/dL
DIHYDROTESTOSTERONE (DHT):DHT : pg/mL
EOSINOPHILS - ABSOLUTE COUNT:AEOS : X 10³ / µL
EOSINOPHILS PERCENTAGE:EOS : %
EPITHELIAL CELLS:UEPIT : cells/HPF
ESTRADIOL (E2):E2 : pg/mL
FERRITIN:FERR : ng/mL
FOLIC ACID:VITB9 : ng/mL
FREE TESTOSTERONE:FTES : pg/mL
FSH:FSH : mIU/mL
GAMMA GLUTAMYL TRANSFERASE (GGT):GGT : U/L
HDL CHOLESTEROL:HCHO : mg/dL
HEPATITIS B SURFACE ANTIGEN(HBSAG) RAPID TEST:HBSAG : #
HOMOCYSTEINE:HOMO : µmol/L
HSCRP:HSCRP : mg/L
INSULIN:INSFA : µIU/mL
INSULIN LIKE GROWTH FACTOR 1:INGF1 : ng/mL
IRON:IRON : µg/dl
LACTATE DEHYDROGENASE (LDH):LDH : U/L
LDL / HDL RATIO:LDL/ : Ratio
LDL CHOLESTEROL - DIRECT:LDL : mg/dL
LEUCOCYTE ESTERASE:ULEST : # (PRESENT/ABSENT)
LIPASE:LASE : U/L
LIPOPROTEIN (a) [Lp(a)]:LPA : mg/dl
LUTEINISING HORMONE (LH):LH : mIU/L
LYMPHOCYTES - ABSOLUTE COUNT:ALYM : X 10³ / µL
LYMPHOCYTES PERCENTAGE:LYMPH : %
MAGNESIUM:MG : mg/dL
MEAN CORPUSCULAR HEMOGLOBIN (MCH):MCH : pg
MEAN CORPUSCULAR HEMOGLOBIN CONCENTRATION (MCHC):MCHC : g/dL
MEAN CORPUSCULAR VOLUME (MCV):MCV : fL
MEAN PLATELET VOLUME (MPV):MPV : fL
MONOCYTES - ABSOLUTE COUNT:AMON : X 10³ / µL
MONOCYTES PERCENTAGE:MONO : %
MUCUS:UMUC : # (PRESENT/ABSENT)
NEUTROPHILS - ABSOLUTE COUNT:ANEU : X 10³ / µL
NEUTROPHILS PERCENTAGE:NEUT : %
NITRITE:UNIT : # (PRESENT/ABSENT)
NON-HDL CHOLESTEROL:NHDL : mg/dL
NUCLEATED RED BLOOD CELLS:NRBC : X 10³ / µL
NUCLEATED RED BLOOD CELLS %:NRBC% : %
PARASITE:UPAR : # (PRESENT/ABSENT)
PH:UPH : # (PRESENT/ABSENT)
PLATELET COUNT:PLT : X 10³ / µL
PLATELET DISTRIBUTION WIDTH (PDW):PDW : fL
PLATELET TO LARGE CELL RATIO (PLCR):PLCR : %
PLATELETCRIT (PCT):PCT : %
POTASSIUM:POT : mmol/L
PROGESTERONE:PROG : ng/mL
PROLACTIN:PRL : ng/mL
PROSTATE SPECIFIC ANTIGEN (PSA):PSA : ng/mL
PROTEIN - TOTAL:PROT : gm/dL
QUICKI:QUICKI : Index
RBC COUNT:RBC : X 10⁶ / µL
RHEUMATOID FACTOR:RFAC : IU/mL
SELENIUM:SEZN : µg/L
SERUM GLOBULIN:SEGB : gm/dL
SERUM GLUTAMIC OXALOACETIC TRANSAMINASE (SGOT):SGOT : U/L
SERUM GLUTAMIC PYRUVIC TRANSAMINASE (SGPT):SGPT : U/L
SEX HORMONE BINDING GLOBULIN (SHBG):SHBG : nmol/L
SODIUM:SOD : mmol/L
SPECIFIC GRAVITY:SPGR : Specific Gravity
TOTAL CHOLESTEROL:CHOL : mg/dL
TESTOSTERONE:TEST : ng/dL
THYROID STIMULATING HORMONE (TSH):USTSH : μIU/mL
TOTAL IRON BINDING CAPACITY:TIBC : µg/dL
TOTAL PROTEIN:PROT : gm/dL
TRANSAMINASE:TRANSAT : U/L
TRIGLYCERIDES:TRIG : mg/dL
TSH - ULTRASENSITIVE:USTSH : μIU/mL
UREA (CALCULATED):UREAC : mg/dL
UREA / SR.CREATININE RATIO:UR/CR : Ratio
URI. ALBUMIN/CREATININE RATIO (UA/C):UA/C : µg/mg of Creatinine
URIC ACID:URIC : mg/dL
URINARY BILIRUBIN:UBIL : # (PRESENT/ABSENT)
URINARY GLUCOSE:UGLU : # (PRESENT/ABSENT)
URINARY LEUCOCYTES (PUS CELLS):ULEUC : cells/HPF
URINARY MICROALBUMIN:UALB : μg/mL
URINARY PROTEIN:UPROT : # (PRESENT/ABSENT)
URINE BLOOD:UBLD : # (PRESENT/ABSENT)
URINE KETONE:UKET : # (PRESENT/ABSENT)
UROBILINOGEN:UBNGN : # (PRESENT/ABSENT)
VITAMIN B-12:VITB : pg/mL
VITAMIN B9/FOLIC ACID:VITB9 : ng/mL
VLDL CHOLESTEROL:VLDL : mg/dL
YEAST:UYST : # (PRESENT/ABSENT)

## UNIT CONVERSION RULES:
- **µg to mg**: divide by 1000
- **mg to µg**: multiply by 1000
- **g to mg**: multiply by 1000
- **mg to g**: divide by 1000
- **ng to µg**: divide by 1000
- **µg to ng**: multiply by 1000
- **pg to ng**: divide by 1000
- **ng to pg**: multiply by 1000
- **mIU to IU**: divide by 1000
- **IU to mIU**: multiply by 1000
- **µIU to mIU**: divide by 1000
- **mIU to µIU**: multiply by 1000

## IMPORTANT NOTES:
1. **Biomarker Format**: Each biomarker is listed as `FULL BIOMARKER NAME:VARIABLE_NAME : unit`
   - Search for the FULL BIOMARKER NAME in the PDF report
   - In the output JSON, use the VARIABLE_NAME (short code after the colon)
   - Example: For "17 OH PROGESTERONE:17OH : ng/mL" → search PDF for "17 OH PROGESTERONE" → output as `{"17OH": value}`
2. **Skip null values** - only include biomarkers that have actual values in the report
3. **Handle alternative names**: ALT=SGPT, AST=SGOT, PCV=Hematocrit, etc.
4. **Convert all units** to match the standardized format exactly
5. **Extract calculated ratios** when available
6. **Use "Male" or "Female"** for sex (never abbreviations)
7. **Include patient demographics** (name, age, sex, cycle)
8. **Qualitative values**: When unit is "#", extract qualitative values like "NON REACTIVE", "POSITIVE", "NEGATIVE", "ABSENT", "PRESENT", "NIL", "TRACE", "NORMAL", "ABNORMAL", etc.
9. **Urine test biomarkers**: For UKET, UMUC, UBLD, UBSAL, UCRYS, ULEST, UPROT, UBPIG, UGLU, UYST, UNIT, UPAR, UBIL, UCAST, UBACT, UBNGN - these are qualitative tests that return "PRESENT" or "ABSENT" or similar text values, NOT numerical values.
10. **CRITICAL**: Look for urine test sections in the report. These biomarkers appear in tables with "ABSENT" or "PRESENT" values. Extract "ABSENT" as the value when found, not 0 or null.
11. **URINE TEST TABLE FORMAT**: Look for tables with columns like "Biomarker Name", "Method", "Result" where:
    - CASTS appears as "CASTS" with result "ABSENT"
    - CRYSTALS appears as "CRYSTALS" with result "ABSENT" 
    - BACTERIA appears as "BACTERIA" with result "ABSENT"
    - YEAST appears as "YEAST" with result "ABSENT"
    - PARASITE appears as "PARASITE" with result "ABSENT"
    Extract the exact text values ("ABSENT" or "PRESENT") from these tables.
12. **SEARCH STRATEGY**: Look for any section containing urine test results, microscopy results, or qualitative test results. These may be in separate sections of the report.
13. **INCLUDE ABSENT VALUES**: When you find urine test biomarkers with "ABSENT" values, include them in the output with "ABSENT" as the value. Do not skip them just because they are "ABSENT".

## OUTPUT FORMAT:
Return a clean JSON object with patient info and only the biomarkers found in the report (no null values).
Use the VARIABLE_NAME (short codes) as JSON keys, NOT the full biomarker names.

Example output format:
```json
{
  "name": "PATIENT NAME",
  "age": 30,
  "sex": "Female",
  "cycle": "All",
  "17OH": 1.2,
  "VITDC": 25.5,
  "SGPT": 28,
  "SGOT": 32,
  "HB": 13.5,
  "TRIG": 120,
  "UBACT": "ABSENT",
  "UCAST": "ABSENT"
}
```

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
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Try to break at a reasonable point
        if end < len(text):
            break_point = end
            for i in range(min(500, chunk_size // 10)):
                if text[end - i] in ['\n', '.', ' ']:
                    break_point = end - i
                    break
            end = break_point
        
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - 2000  # Overlap for better coverage
        
    return chunks

async def process_chunk_async(chunk: str, api_key: str, chunk_num: int, total_chunks: int, semaphore: asyncio.Semaphore) -> dict | None:
    """Process a single chunk asynchronously with Claude API."""
    async with semaphore:  # Limit concurrent requests
        try:
            print(f"Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} chars)...")
            
            # Add delay to avoid rate limits
            if chunk_num > 1:
                delay = (chunk_num - 1) * 2  # 2 seconds delay between chunks
                print(f"Waiting {delay} seconds to avoid rate limits...")
                await asyncio.sleep(delay)
            
            # Create client for this request
            client = anthropic.AsyncAnthropic(api_key=api_key)
            
            # Create message
            message = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4096,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": f"{ASYNC_PROMPT}\n\n---REPORT TEXT CHUNK {chunk_num}---\n{chunk}"
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
            print(f"Rate limit hit on chunk {chunk_num}. Waiting 30 seconds...")
            await asyncio.sleep(30)
            return None
        except Exception as e:
            print(f"Error processing chunk {chunk_num}: {e}")
            return None

def merge_results(results: list[dict]) -> dict:
    """Merge results from multiple chunks."""
    if not results:
        return {}
    
    merged = {
        "name": "Unknown",
        "age": None,
        "sex": "Unknown",
        "cycle": "All"
    }
    
    for result in results:
        # Extract patient info
        if "name" in result:
            merged["name"] = result["name"]
        if "age" in result:
            merged["age"] = result["age"]
        if "sex" in result:
            merged["sex"] = result["sex"]
        
        # Merge biomarkers
        for key, value in result.items():
            if key not in ["name", "age", "sex", "cycle"] and value is not None:
                merged[key] = value
    
    return merged

async def process_pdf_async(pdf_path: str, api_key: str, max_concurrent: int = 2) -> dict | None:
    """Process PDF asynchronously with multiple chunks."""
    print(f"Extracting text from PDF...")
    full_text = extract_text_from_pdf(pdf_path)
    
    if not full_text.strip():
        print("Error: Could not extract text from PDF")
        return None
    
    print(f"Extracted {len(full_text)} characters")
    
    chunks = split_text_into_chunks(full_text, 35000)
    print(f"Split into {len(chunks)} chunks")
    
    # Create semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Process all chunks concurrently
    tasks = [
        process_chunk_async(chunk, api_key, i+1, len(chunks), semaphore)
        for i, chunk in enumerate(chunks)
    ]
    
    print(f"Processing {len(tasks)} chunks concurrently (max {max_concurrent} at a time)...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out exceptions and None results
    valid_results = [r for r in results if isinstance(r, dict) and r is not None]
    
    if not valid_results:
        print("No data extracted from any chunk.")
        return None
    
    print(f"✓ Successfully processed {len(valid_results)} chunks")
    return merge_results(valid_results)

async def main_async():
    parser = argparse.ArgumentParser(description="Extract Thyrocare data using asynchronous processing.")
    parser.add_argument("pdf_path", help="Path to PDF file")
    parser.add_argument("-o", "--output", help="Output JSON file path", default=None)
    parser.add_argument("--api-key", help="Anthropic API key", default=None)
    parser.add_argument("--max-concurrent", type=int, default=2, help="Maximum concurrent requests")
    
    args = parser.parse_args()
    
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    output_path = args.output or str(Path(args.pdf_path).with_suffix('')) + '_async.json'
    
    print(f"Processing: {args.pdf_path}")
    print(f"Output: {output_path}")
    print(f"Max concurrent requests: {args.max_concurrent}")
    print("-" * 50)
    
    start_time = time.time()
    result = await process_pdf_async(args.pdf_path, api_key, args.max_concurrent)
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

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()

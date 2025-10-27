import json

# Load from file instead of inline variable
with open("biomarkers.json", "r") as f:
    data = json.load(f)

unique_biomarkers = set()

for item in data:
    biomarkers = item.get("Tracking Biomarkers", "")
    if biomarkers:
        for biomarker in biomarkers.split(","):
            cleaned = biomarker.strip()
            if cleaned:
                unique_biomarkers.add(cleaned)

print(sorted(unique_biomarkers))

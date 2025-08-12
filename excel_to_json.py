import pandas as pd
import json

# === Load Excel ===
excel_file = r'C:\Users\Admin\Downloads\PMX_Sample_report.xlsx'
df = pd.read_excel(excel_file)
df.fillna("", inplace=True)

# === Section Metadata ===
section_info = {
    "CARDIAC HEALTH": {
        "title": "CARDIAC HEALTH",
        "content": "Cardiac health refers to the overall well-being and optimal functioning of the heart and its associated vascular system. It is a critical aspect of overall health, as the heart is responsible for pumping oxygenated blood and essential nutrients throughout the body. ",
    },
    "METABOLIC HEALTH": {
        "title": "METABOLIC HEALTH",
        "content": "Metabolic health refers to the state of having ideal levels of blood sugar, triglycerides, HDL cholesterol, blood pressure, and waist circumference, reducing risks of diabetes, heart disease, stroke, and improving overall quality of life and longevity.",
    },
    "VASCULAR HEALTH": {
        "title": "VASCULAR HEALTH",
        "content": "Vascular health refers to the proper functioning of blood vessels, ensuring efficient circulation of blood, oxygen, and nutrients throughout the body. It plays a vital role in preventing cardiovascular diseases, supporting organ function, and maintaining overall well-being.",
    },
    "Gut and Immune Health": {
        "title": "Gut and Immune Health",
        "content": "Gut and Immune Health are interconnected, with 70% of immune cells residing in the gut. A healthy microbiome supports digestion, immunity, and inflammation control. Boost gut health with fiber, probiotics, and hydration while avoiding processed foods. This balance strengthens immunity and overall well-being.",
    },
    "Kidney and Liver Health": {
        "title": "Kidney and Liver Health",
        "content": "Kidney and Liver Health is vital for detoxification, metabolism, and body function. The kidneys filter waste and maintain fluid balance, while the liver processes nutrients and detoxifies harmful substances. Support them with hydration, a balanced diet, limited alcohol, and avoiding excess salt or processed foods.",
    },
    "Neuro Health": {
        "title": "Neuro Health",
        "content": "Neuro Health is vital for cognitive function, memory, and nervous system efficiency. A healthy brain aids decision-making, mood, and sensory responses. Support it with a nutrient-rich diet, exercise, mental stimulation, sleep, stress management, and avoiding harmful substances for optimal performance.",
    },
    "Mood Disorders": {
        "title": "Mood Disorders",
        "content": "Mood Disorders affect emotional well-being, causing conditions like depression, anxiety, or bipolar disorder. Manage them with therapy, medication, exercise, a balanced diet, stress management, and support networks for better emotional health and quality of life.",
    },
    "MUSCLE AND BONE HEALTH": {
        "title": "MUSCLE AND BONE HEALTH",
        "content": "Ensures strength, mobility, and resilience by maintaining optimal muscle mass and bone density. It reduces the risk of osteoporosis, fractures, and age-related muscle loss. Proper nutrition, exercise, and lifestyle habits are key to supporting long-term skeletal and muscular well-being.",
    },
    "Aging and Longevity": {
        "title": "Aging and Longevity",
        "content": "Focus on maintaining health and vitality as we age. Healthy aging involves balanced nutrition, regular exercise, mental stimulation, and stress management. Preventive care and lifestyle choices can delay age-related issues, improving quality of life and promoting a longer, healthier lifespan.",
    },
    "Eye Health": {
        "title": "Eye Health",
        "content": "Eye Health ensures clear vision and quality of life. Conditions like macular degeneration, glaucoma, and cataracts can impair vision if untreated. Protect eyes with regular checkups, good nutrition, UV protection, limiting screen time, and staying hydrated to ensure long-term visual health.",
    },
    "Nutrition": {
        "title": "Nutrition",
        "content": "Nutrition is key to health, providing essential nutrients for energy, growth, and repair. A balanced diet supports immunity, brain function, and overall well-being. Proper hydration, mindful eating, and healthy food choices enhance long-term health and vitality.",
    },
    "Methylation Genes": {
        "title": "Methylation Genes",
        "content": "Regulate biological processes by controlling gene expression without altering DNA. Proper methylation supports detoxification, hormone balance, and DNA repair. Support it with a nutrient-rich diet, B-vitamins, exercise, and stress management to maintain overall health.",
    },
    "Liver Detox Phase 1": {
        "title": "Liver Detox Phase 1",
        "content": "Liver detoxification starts with Phase 1, where enzymes break down toxins for further processing. Gene variations can affect this process, influencing toxin clearance, health, and drug response.",
    },
    "Liver Detox Phase 2": {
        "title": "Liver Detox Phase 2",
        "content": "Phase II liver detoxification makes toxins water-soluble for easier elimination. Gene variations can affect how well the body clears pollutants, drugs, and harmful byproducts.",
    },
    "Hereditary Cancer Risk": {
        "title": "Hereditary Cancer",
        "content": "Risk involves genetic mutations passed through families that increase cancer risk, such as in BRCA1 or BRCA2 genes. Early screening, genetic counseling, and lifestyle changes help manage risks. Awareness and prevention are key to reducing the impact of hereditary cancers.",
    }
}
# === Build Final Structured JSON ===
final_output = {}

for group, info in section_info.items():
    section_data = []
    group_df = df[df["GROUP"] == group.upper()]

    for _, row in group_df.iterrows():
        condition = row["CONDITION"]
        section_data.append({
            "header": condition,
            "header_data": row["DEFINITION"],
            "range": row["RISK LEVEL"],
            "genes_analyzed": row["TOP LIST OF GENES ANALYZED"],
            "interpretation": row["INTERPRETATION"]
        })

    key_name = group.lower().replace(" ", "_") + "_data"
    final_output[key_name] = {
        "title": info["title"],
        "content": info["content"],
        "data": section_data
    }

# === Save Output ===
with open("final_output.json", "w", encoding="utf-8") as f:
    json.dump(final_output, f, ensure_ascii=False, indent=4)

print("✅ All health sections processed and saved to final_output.json")


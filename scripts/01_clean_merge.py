import pandas as pd
import numpy as np

# ============================================================
# Maharashtra Crop Risk Model
# Step 1: Load, Clean, Merge & Calculate Risk Score
# ============================================================

# --- Load Data ---
crop = pd.read_csv('raw_data/ICRISAT-District_Level_Data.csv')
rain = pd.read_csv('raw_data/rainfall_maharashtra.csv')

# --- Select Key Crops ---
key_crops_area = [
    'SORGHUM AREA (1000 ha)', 'PIGEONPEA AREA (1000 ha)',
    'COTTON AREA (1000 ha)', 'SOYABEAN AREA (1000 ha)',
    'SUGARCANE AREA (1000 ha)', 'WHEAT AREA (1000 ha)',
    'RICE AREA (1000 ha)', 'CHICKPEA AREA (1000 ha)'
]
key_crops_yield = [
    'SORGHUM YIELD (Kg per ha)', 'PIGEONPEA YIELD (Kg per ha)',
    'COTTON YIELD (Kg per ha)', 'SOYABEAN YIELD (Kg per ha)',
    'SUGARCANE YIELD (Kg per ha)', 'WHEAT YIELD (Kg per ha)',
    'RICE YIELD (Kg per ha)', 'CHICKPEA YIELD (Kg per ha)'
]

# --- Clean Crop Data ---
crop_clean = crop[['Dist Name', 'Year'] + key_crops_area + key_crops_yield].copy()

# --- Merge Crop + Rainfall ---
merged = pd.merge(crop_clean, rain, on=['Dist Name', 'Year'], how='inner')
print("Merged shape:", merged.shape)

# ============================================================
# Step 2: Calculate Crop Risk Score
# ============================================================

# District-wise average yield (baseline)
baseline = merged.groupby('Dist Name')[key_crops_yield].transform('mean')

# Yield deviation from baseline (%)
for col in key_crops_yield:
    crop_name = col.split(' YIELD')[0]
    merged[f'{crop_name}_yield_dev'] = ((merged[col] - baseline[col]) / (baseline[col] + 1)) * 100

# Average yield deviation across all crops
dev_cols = [c for c in merged.columns if '_yield_dev' in c]
merged['avg_yield_dev'] = merged[dev_cols].mean(axis=1)

# Normalize function
def normalize(series):
    return (series - series.min()) / (series.max() - series.min() + 0.001)

# Risk Score Components:
# 40% Rainfall deviation + 40% Yield deviation + 20% Drought flag
rain_risk  = normalize(-merged['Rainfall_Deviation_pct'])
yield_risk = normalize(-merged['avg_yield_dev'])
drought_risk = merged['Drought_Flag']

merged['Crop_Risk_Score'] = (
    (rain_risk * 0.40) +
    (yield_risk * 0.40) +
    (drought_risk * 0.20)
) * 100
merged['Crop_Risk_Score'] = merged['Crop_Risk_Score'].round(2)

# Risk Category
def risk_cat(score):
    if score >= 70:   return 'HIGH'
    elif score >= 40: return 'MEDIUM'
    else:             return 'LOW'

merged['Risk_Category'] = merged['Crop_Risk_Score'].apply(risk_cat)

# --- Save Final Output ---
merged.to_csv('cleaned_data/final_risk_data.csv', index=False)
print("Done! File saved to cleaned_data/final_risk_data.csv")
print(merged[['Dist Name','Year','Crop_Risk_Score','Risk_Category']].head(10))

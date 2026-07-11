import pandas as pd
import sqlite3
import os

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CSV_PATH   = os.path.join(BASE_DIR, '..', 'cleaned_data', 'final_risk_data.csv')
DB_PATH    = os.path.join(BASE_DIR, '..', 'maharashtra_crop_risk.db')

# ── Load CSV ───────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_PATH)
df.columns = df.columns.str.strip()          # remove any accidental spaces
print(f"✅ CSV loaded  →  {len(df)} rows, {len(df.columns)} columns")

# ── Connect to SQLite ──────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Table 1 : district_risk  (main fact table) ─────────────────────────────────
df.to_sql('district_risk', conn, if_exists='replace', index=False)
print(f"✅ Table 'district_risk' created  →  {len(df)} rows")

# ── Table 2 : district_summary  (avg risk score per district) ─────────────────
summary_query = """
CREATE TABLE IF NOT EXISTS district_summary AS
SELECT
    "Dist Name"                         AS district,
    ROUND(AVG(Crop_Risk_Score), 2)      AS avg_risk_score,
    ROUND(AVG(Annual_Rainfall_mm), 1)   AS avg_rainfall_mm,
    ROUND(AVG(Rainfall_Deviation_pct), 1) AS avg_rainfall_dev_pct,
    SUM(Drought_Flag)                   AS total_drought_years,
    COUNT(*)                            AS years_of_data,
    -- Most frequent risk category
    (SELECT Risk_Category
     FROM district_risk r2
     WHERE r2."Dist Name" = r."Dist Name"
     GROUP BY Risk_Category
     ORDER BY COUNT(*) DESC
     LIMIT 1)                           AS dominant_risk_category
FROM district_risk r
GROUP BY "Dist Name"
ORDER BY avg_risk_score DESC;
"""

cursor.execute("DROP TABLE IF EXISTS district_summary")
cursor.execute(summary_query)
conn.commit()

summary_count = cursor.execute("SELECT COUNT(*) FROM district_summary").fetchone()[0]
print(f"✅ Table 'district_summary' created  →  {summary_count} districts")

# ── Table 3 : yearly_trend  (Maharashtra-wide avg per year) ───────────────────
trend_query = """
CREATE TABLE IF NOT EXISTS yearly_trend AS
SELECT
    Year,
    ROUND(AVG(Crop_Risk_Score), 2)        AS avg_risk_score,
    ROUND(AVG(Annual_Rainfall_mm), 1)     AS avg_rainfall_mm,
    ROUND(AVG(Rainfall_Deviation_pct), 1) AS avg_rainfall_dev_pct,
    SUM(Drought_Flag)                     AS districts_in_drought,
    COUNT(*)                              AS districts_reported
FROM district_risk
GROUP BY Year
ORDER BY Year;
"""

cursor.execute("DROP TABLE IF EXISTS yearly_trend")
cursor.execute(trend_query)
conn.commit()

trend_count = cursor.execute("SELECT COUNT(*) FROM yearly_trend").fetchone()[0]
print(f"✅ Table 'yearly_trend' created  →  {trend_count} years")

# ── Quick Validation ───────────────────────────────────────────────────────────
print("\n── Top 5 High-Risk Districts (avg score) ──────────────────────────────")
top5 = cursor.execute("""
    SELECT district, avg_risk_score, total_drought_years, dominant_risk_category
    FROM district_summary
    ORDER BY avg_risk_score DESC
    LIMIT 5
""").fetchall()
for row in top5:
    print(f"  {row[0]:<20}  Risk Score: {row[1]}  Droughts: {row[2]}  Category: {row[3]}")

print("\n── Drought Years (Maharashtra-wide) ──────────────────────────────────")
droughts = cursor.execute("""
    SELECT Year, districts_in_drought, avg_risk_score
    FROM yearly_trend
    WHERE districts_in_drought > 5
    ORDER BY districts_in_drought DESC
    LIMIT 5
""").fetchall()
for row in droughts:
    print(f"  Year: {row[0]}  Districts in drought: {row[1]}  Avg risk: {row[2]}")

# ── Done ───────────────────────────────────────────────────────────────────────
conn.close()
print(f"\n🎉 Database saved  →  {DB_PATH}")

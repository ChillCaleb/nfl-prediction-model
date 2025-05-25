import sqlite3
import pandas as pd
from pathlib import Path

# === Paths ===
db_path = "Database/nfl_player_data.db"
csv_root = Path("NFL")

# === Connect ===
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === Clean Old Tables (except league-wide) ===
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
existing_tables = {row[0] for row in cursor.fetchall()}
league_tables = {t for t in existing_tables if t.startswith("league_")}
for t in existing_tables - league_tables:
    cursor.execute(f"DROP TABLE IF EXISTS {t}")
conn.commit()

# === Table Map ===
csv_table_map = {
    "defense.csv": "defense",
    "rushing_and_receiving.csv": "rushing_and_receiving",
    "passing.csv": "passing",
    "advanced_defense.csv": "advanced_defense",
    "advanced_passing.csv": "advanced_passing",
    "advanced_receiving.csv": "advanced_receiving",
    "advanced_rushing.csv": "advanced_rushing",
}

# === Insert Data ===
for file_name, table_name in csv_table_map.items():
    for csv_file in csv_root.rglob(file_name):
        if "raw_data" in str(csv_file).lower():
            continue  # Skip raw_data league-wide sources

        try:
            team = csv_file.parts[-2].lower()
            df = pd.read_csv(csv_file)
            df.insert(0, "Team", team)
            df.to_sql(table_name, conn, if_exists="append", index=False)
            print(f"[✓] Inserted {len(df)} rows into '{table_name}' for {team}")
        except Exception as e:
            print(f"[!] Failed to insert {csv_file}: {e}")

conn.commit()
conn.close()
print("✅ Database rebuild complete.")

import sqlite3
import pandas as pd
from pathlib import Path

# Setup
db_path = "nfl_player_data.db"
raw_data_path = Path("NFL/raw_data")

# League-wide files and target table names
league_files = {
    "Total_Offense.csv": "total_offense",
    "Total_Defense.csv": "total_defense",
    "Total_Special_teams.csv": "total_special_teams",
    "Full_Schedule.csv": "full_schedule"
}

# Connect to DB
conn = sqlite3.connect(db_path)

for filename, table in league_files.items():
    csv_path = raw_data_path / filename
    try:
        df = pd.read_csv(csv_path)

        # Optional: strip spaces from column names for safety
        df.columns = df.columns.str.strip()

        # Store in SQLite
        df.to_sql(table, conn, if_exists="replace", index=False)
        print(f"[✓] Inserted {len(df)} rows into {table}")
    except Exception as e:
        print(f"[!] Failed to load {filename}: {e}")

conn.commit()
conn.close()
print("✅ League-wide tables inserted successfully.")

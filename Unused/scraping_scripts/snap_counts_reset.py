import sqlite3
import pandas as pd
from pathlib import Path

# === CONFIGURATION ===
db_path = "Database/nfl_player_data.db"
snap_dir = Path("NFL/raw_data/snap_counts")

# === CONNECT TO DATABASE ===
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === DROP TABLES THAT COULD CONFLICT ===
cursor.execute("DROP TABLE IF EXISTS snap_counts;")
cursor.execute("VACUUM;")  # Ensures schema is fully cleared
conn.commit()
print("🗑️ Hard dropped and vacuumed snap_counts")

# === CLEAN UP any leftover team_snaps_* tables ===
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'team_snaps_%';")
for (table,) in cursor.fetchall():
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    print(f"🗑️ Dropped: {table}")
conn.commit()

# === LOAD AND CLEAN CSVs ===
all_snap_data = []
for file in snap_dir.glob("*.csv"):
    try:
        team = file.stem.split("_")[1].lower()
        df = pd.read_csv(file)
        df.insert(0, "Team", team)
        all_snap_data.append(df)
        print(f"[✓] Processed: {file.name}")
    except Exception as e:
        print(f"[!] Error processing {file.name}: {e}")

# === CREATE CLEAN snap_counts TABLE ===
if all_snap_data:
    final_df = pd.concat(all_snap_data, ignore_index=True)
    final_df.to_sql("snap_counts", conn, if_exists="replace", index=False)
    print(f"✅ Inserted {len(final_df)} rows into unified snap_counts table.")

conn.commit()
conn.close()
print("✅ Database updated successfully.")

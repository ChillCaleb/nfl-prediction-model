import sqlite3
import pandas as pd
import os

# === Paths ===
snap_count_dir = "NFL/raw_data/snap_counts"
db_path = "Database/nfl_player_data.db"

# === Connect to database ===
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === Drop the global snap_counts table ===
cursor.execute("DROP TABLE IF EXISTS snap_counts;")
conn.commit()
print("🗑️ Dropped: snap_counts")

# === Read and stack all CSVs as-is ===
all_data = []

for file in os.listdir(snap_count_dir):
    if file.endswith(".csv"):
        df = pd.read_csv(os.path.join(snap_count_dir, file))
        all_data.append(df)
        print(f"[✓] Loaded: {file}")

# === Merge and store globally ===
if all_data:
    final_df = pd.concat(all_data, ignore_index=True)
    final_df.to_sql("snap_counts", conn, if_exists="replace", index=False)
    print(f"✅ Stored {len(final_df)} rows in snap_counts")

conn.commit()
conn.close()
print("✅ Done.")

import sqlite3
import pandas as pd

# Paths
snap_db = "Database/nfl_player_data.db"       # contains snap_counts_*
main_db = "Database/nfl_player_data2.db"      # has everything else

# Connect to both
conn_snap = sqlite3.connect(snap_db)
conn_main = sqlite3.connect(main_db)

# Get snap count tables from snap_db
cursor = conn_snap.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'snap_counts_%';")
snap_tables = [row[0] for row in cursor.fetchall()]

# Copy each table into the main DB
for table in snap_tables:
    print(f"📥 Merging table: {table}")
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn_snap)
    df.to_sql(table, conn_main, if_exists="replace", index=False)

print("✅ Merge complete.")
conn_main.commit()
conn_main.close()
conn_snap.close()

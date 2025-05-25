import sqlite3

# Path to your DB
db_path = "Database/nfl_player_data.db"

# Connect to DB
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Find and drop all tables that start with "team_snaps_"
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'team_snaps_%';")
team_snap_tables = [row[0] for row in cursor.fetchall()]

for table in team_snap_tables:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    print(f"🗑️ Dropped: {table}")

conn.commit()
conn.close()
print("✅ All team snap count tables deleted.")

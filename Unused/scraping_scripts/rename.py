import sqlite3

db_path = "Database/nfl_player_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all misnamed snap count tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'team_snaps_%';")
wrong_tables = [row[0] for row in cursor.fetchall()]

for old_name in wrong_tables:
    team = old_name.replace("team_snaps_", "")
    new_name = f"team_{team}_snaps"
    try:
        cursor.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}";')
        print(f"✅ Renamed {old_name} → {new_name}")
    except sqlite3.OperationalError as e:
        print(f"⚠️ Could not rename {old_name}: {e}")

conn.commit()
conn.close()

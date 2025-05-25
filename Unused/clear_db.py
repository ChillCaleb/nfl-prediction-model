import sqlite3

# Path to your database
db_path = "nfl_player_data.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Drop each table
for table_name in tables:
    print(f"Dropping table: {table_name[0]}")
    cursor.execute(f"DROP TABLE IF EXISTS {table_name[0]}")

conn.commit()
conn.close()
print("✅ All tables deleted from database.")

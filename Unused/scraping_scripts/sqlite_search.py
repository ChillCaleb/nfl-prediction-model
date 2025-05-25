import sqlite3

# Replace this with your full path if needed
db_path = "/Users/calebbanks/NFL_predict/Database/nfl_player_data.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Query all tables in the database
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("📂 Tables in the database:")
for table in tables:
    print("-", table[0])

conn.close()

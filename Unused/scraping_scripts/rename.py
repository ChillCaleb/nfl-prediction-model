# rename_ratings_tables.py
# One-time script to rename defensive ratings tables in the database

import sqlite3

# --- CONFIG ---
RATINGS_DB_PATH = "Database/nfl_ratings.db"

# --- CONNECT ---
conn = sqlite3.connect(RATINGS_DB_PATH)
cursor = conn.cursor()

# --- RENAME TABLES ---
try:
    cursor.execute("ALTER TABLE player_ratings RENAME TO Defensive_player_ratings;")
    print("Renamed 'player_ratings' to 'Defensive_player_ratings'")
except sqlite3.OperationalError as e:
    print("player_ratings rename failed:", e)

try:
    cursor.execute("ALTER TABLE team_ratings RENAME TO Defensive_team_ratings;")
    print("Renamed 'team_ratings' to 'Defensive_team_ratings'")
except sqlite3.OperationalError as e:
    print("team_ratings rename failed:", e)

# --- CLOSE CONNECTION ---
conn.commit()
conn.close()

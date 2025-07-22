import sqlite3

# Path to the ratings database
ratings_db_path = "Database/nfl_ratings.db"

# Connect to the database
conn = sqlite3.connect(ratings_db_path)
cursor = conn.cursor()

# List of tables to clear
tables = ["player_ratings", "team_ratings"]

# Delete all records from each table
for table in tables:
    try:
        cursor.execute(f"DELETE FROM {table}")
        print(f"Cleared table: {table}")
    except sqlite3.OperationalError as e:
        print(f"Error with table {table}: {e}")

# Commit changes and close connection
conn.commit()
conn.close()

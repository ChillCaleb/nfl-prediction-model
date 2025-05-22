import sqlite3
import pandas as pd
import os

DB_NAME = "nfl_player_data.db"

def get_connection():
    """Creates and returns a connection to the SQLite database."""
    return sqlite3.connect(DB_NAME)

def store_to_db(df: pd.DataFrame, table_name: str, if_exists: str = "replace"):
    """
    Stores a DataFrame into the SQLite database.

    Args:
        df (pd.DataFrame): The DataFrame to store.
        table_name (str): Table name in the database.
        if_exists (str): What to do if table exists (default 'replace')
    """
    with get_connection() as conn:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        print(f"[DB] Stored {len(df)} records in table '{table_name}'")

def query_db(query: str) -> pd.DataFrame:
    """
    Executes a SQL query and returns the results as a DataFrame.

    Args:
        query (str): SQL query string.

    Returns:
        pd.DataFrame: Query result
    """
    with get_connection() as conn:
        return pd.read_sql(query, conn)

def list_tables():
    """
    Lists all tables in the database.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        return tables

if __name__ == "__main__":
    # Example usage: Load a CSV and store it
    example_csv = "player_data/phi_2023_players.csv"
    if os.path.exists(example_csv):
        df = pd.read_csv(example_csv)
        store_to_db(df, "phi_2023_players")

        # Run a simple test query
        qb_df = query_db("SELECT * FROM phi_2023_players WHERE Pos = 'QB'")
        print(qb_df)
    else:
        print("[INFO] Example file not found.")

import os
import pandas as pd
from Database.player_database import store_to_db

# Define base paths
TEAM_BASE_DIR = "NFL"
LEAGUE_WIDE_DIR = "NFL/raw_data"


def ingest_league_csvs(base_dir=LEAGUE_WIDE_DIR):
    print("\n📥 Ingesting league-wide CSVs...")
    for file in os.listdir(base_dir):
        if file.endswith(".csv"):
            path = os.path.join(base_dir, file)
            df = pd.read_csv(path)

            # Derive table name from filename
            table_name = f"league_{file.replace('.csv', '').lower()}"
            store_to_db(df, table_name, if_exists="replace")


def ingest_team_csvs(base_dir=TEAM_BASE_DIR):
    print("\n📥 Ingesting team-specific CSVs...")
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)

                # Derive team name from path (e.g. "ravens" from path)
                path_parts = root.lower().split(os.sep)
                try:
                    team_index = path_parts.index("nfl") + 3  # nfl -> conference -> division -> team
                    team = path_parts[team_index]
                except (ValueError, IndexError):
                    print(f"⚠️ Skipping unrecognized structure: {file_path}")
                    continue

                table_name = f"team_{team}_{file.replace('.csv', '').lower()}"
                try:
                    df = pd.read_csv(file_path)
                    df.insert(0, "team", team)  # Add team column for easier filtering later
                    store_to_db(df, table_name, if_exists="replace")
                except Exception as e:
                    print(f"❌ Failed to ingest {file_path}: {e}")


if __name__ == "__main__":
    ingest_league_csvs()
    ingest_team_csvs()

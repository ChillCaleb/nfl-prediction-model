import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import numpy as np
from Database.player_database import query_db, store_to_db

def load_players_by_team(team: str, year: int, position: str = None) -> pd.DataFrame:
    table_name = f"{team.lower()}_{year}_players"
    if position:
        query = f"SELECT * FROM {table_name} WHERE Pos = '{position}'"
    else:
        query = f"SELECT * FROM {table_name}"
    try:
        return query_db(query)
    except Exception as e:
        print(f"[ERROR] Could not load data for {team} ({year}) position {position}: {e}")
        return pd.DataFrame()

# Rating functions by position
def rate_qb(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    df = df.fillna(0)
    score = (df["TD"] * 6 + df["Pass Yds"] * 0.04 - df["INT"] * 2).sum()
    return score / len(df)

def rate_rb(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    df = df.fillna(0)
    score = (df["Rush Yds"] * 0.1 + df["TD"] * 6).sum()
    return score / len(df)

def rate_wr(df: pd.DataFrame) -> float:
    if df.empty:
        return 0
    df = df.fillna(0)
    score = (df["Rec Yds"] * 0.1 + df["TD"] * 6).sum()
    return score / len(df)

def get_team_positional_ratings(team: str, year: int) -> dict:
    ratings = {}
    for position, rater in {
        "QB": rate_qb,
        "RB": rate_rb,
        "WR": rate_wr
    }.items():
        player_df = load_players_by_team(team, year, position)
        ratings[position] = rater(player_df)
    return ratings

if __name__ == "__main__":
    # Example scrape+store usage
    team = input("Enter team name (e.g., 'PHI'): ").strip()
    year = int(input("Enter year (e.g., 2023): "))
    csv_path = f"player_data/{team.lower()}_{year}_players.csv"

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        store_to_db(df, f"{team.lower()}_{year}_players")
        print(f"[INFO] Loaded {len(df)} rows from {csv_path} into DB.")

        ratings = get_team_positional_ratings(team, year)
        print(f"Player-based positional ratings for {team} ({year}):")
        for position, rating in ratings.items():
            print(f"  {position}: {rating:.2f}")
    else:
        print(f"[WARN] File not found: {csv_path}")

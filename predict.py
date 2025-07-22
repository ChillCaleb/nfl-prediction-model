# predict.py

import pandas as pd
import numpy as np
import sqlite3
from probability_models import MODEL_REGISTRY, logistic_win_probability
from Legacy_Files.Engine.data_loader import get_schedule_df

DB_PATH = "Database/nfl_ratings.db"

TEAM_NAME_ALIASES = {
    "Arizona Cardinals": "cardinals",
    "Atlanta Falcons": "falcons",
    "Baltimore Ravens": "ravens",
    "Buffalo Bills": "bills",
    "Carolina Panthers": "panthers",
    "Chicago Bears": "bears",
    "Cincinnati Bengals": "bengals",
    "Cleveland Browns": "browns",
    "Dallas Cowboys": "cowboys",
    "Denver Broncos": "broncos",
    "Detroit Lions": "lions",
    "Green Bay Packers": "packers",
    "Houston Texans": "texans",
    "Indianapolis Colts": "colts",
    "Jacksonville Jaguars": "jaguars",
    "Kansas City Chiefs": "chiefs",
    "Las Vegas Raiders": "raiders",
    "Los Angeles Chargers": "chargers",
    "Los Angeles Rams": "rams",
    "Miami Dolphins": "dolphins",
    "Minnesota Vikings": "vikings",
    "New England Patriots": "patriots",
    "New Orleans Saints": "saints",
    "New York Giants": "giants",
    "New York Jets": "jets",
    "Philadelphia Eagles": "eagles",
    "Pittsburgh Steelers": "steelers",
    "San Francisco 49ers": "49ers",
    "Seattle Seahawks": "seahawks",
    "Tampa Bay Buccaneers": "buccaneers",
    "Tennessee Titans": "titans",
    "Washington Commanders": "commanders"
}


def get_team_rating(team_abbr):
    team_key = TEAM_NAME_ALIASES.get(team_abbr.strip())
    if not team_key:
        raise ValueError(f"Unknown team alias for: {team_abbr}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT total FROM Offensive_team_ratings WHERE team = ?", (team_key,))
    offense_result = cursor.fetchone()

    cursor.execute("SELECT total FROM Defensive_team_ratings WHERE team = ?", (team_key,))
    defense_result = cursor.fetchone()

    conn.close()

    if offense_result is None or defense_result is None:
        raise ValueError(f"No rating found in DB for team: {team_key}")

    return offense_result[0], defense_result[0]

def calc_overall_rating(team_abbr):
    offense, defense = get_team_rating(team_abbr)
    return 0.5 * offense + 0.5 * defense

def simulate_season(model_name="outperform"):
    print(f"\n🗕 Starting simulation using '{model_name}' model...")
    schedule = get_schedule_df()
    schedule = schedule.dropna(subset=["Winner/tie", "Loser/tie"])

    teams = pd.unique(schedule[["Winner/tie", "Loser/tie"]].values.ravel())
    wins = {team: 0 for team in teams}
    losses = {team: 0 for team in teams}

    model_func = MODEL_REGISTRY.get(model_name)
    if model_func is None:
        raise ValueError(f"Unknown model: {model_name}")

    for _, game in schedule.iterrows():
        team1 = game["Winner/tie"]
        team2 = game["Loser/tie"]

        r1 = calc_overall_rating(team1)
        r2 = calc_overall_rating(team2)

        if model_name == "outperform":
            prob = model_func(r1, r2, pd.Series([r1, r2]))
        elif model_name == "bayesian":
            prior = 0.5
            likelihood = logistic_win_probability(r1 - r2)
            evidence = 1.0
            prob = model_func(prior, likelihood, evidence)
        elif model_name == "elo_expected":
            prob = model_func(r1, r2)
        elif model_name == "elo_update":
            prob = model_func(r1, r2, k=20, outcome=1)
        else:
            prob = model_func(r1 - r2)

        winner = team1 if np.random.rand() < prob else team2
        loser = team2 if winner == team1 else team1

        wins[winner] += 1
        losses[loser] += 1

    standings = pd.DataFrame({
        "Team": list(wins.keys()),
        "Wins": list(wins.values()),
        "Losses": list(losses.values())
    }).sort_values(["Wins", "Losses"], ascending=[False, True]).reset_index(drop=True)

    print("\n🎲 Probabilistic Season Results Using Model:", model_name)
    print(standings.to_string(index=False))

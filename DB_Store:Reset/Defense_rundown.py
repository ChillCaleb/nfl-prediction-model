# zzzzz_last_fill.py — loops through all teams except the 49ers

import sqlite3
import pandas as pd
from Engine import defense, strength_of_schedule
from Ratings.Defense.cb import rate_cb
from Ratings.Defense.dl import rate_dl
from Ratings.Defense.lb import rate_lb
from Ratings.Defense.safety import rate_safety
from Engine.constants import abbr_to_full, full_to_abbr, team_name_alias

# --- CONFIG ---
DB_PATH = "Database/nfl_player_data.db"
RATINGS_DB_PATH = "Database/nfl_ratings.db"

# --- IMPACT FORMULAS BY POSITION ---
def calc_rushing_impact(def_row, adv_row, group):
    if group == 'D':
        return def_row.get("TFL", 0) + adv_row.get("Run_Stops", 0)
    elif group == 'L':
        return def_row.get("Solo", 0) + adv_row.get("Run_Stops", 0)
    elif group in ['S', 'C']:
        return def_row.get("Solo", 0)
    return 0

def calc_passing_impact(def_row, adv_row, group):
    if group == 'D':
        return def_row.get("Sk", 0) + adv_row.get("Prss", 0)
    elif group == 'L':
        return def_row.get("Sk", 0) + def_row.get("Int", 0) + adv_row.get("Tgt_Rate", 0)
    elif group == 'C':
        return adv_row.get("Bats", 0) + def_row.get("Int", 0) + adv_row.get("Tgt_Rate", 0)
    elif group == 'S':
        return def_row.get("Int", 0) + adv_row.get("Prss", 0) + adv_row.get("Tgt_Rate", 0)
    return 0

def calc_scoring_impact(def_row, adv_row, group):
    return def_row.get("Int", 0) - adv_row.get("TD", 0)

rate_map = {
    'C': rate_cb,
    'D': rate_dl,
    'L': rate_lb,
    'S': rate_safety
}

# --- LOOP THROUGH TEAMS ---
for TEAM_ABBR in abbr_to_full:
    if TEAM_ABBR == "SF":
        continue

    TEAM_NAME_DEF = team_name_alias[TEAM_ABBR]
    TEAM_NAME_SNAP = TEAM_NAME_DEF.title()

    # --- LOAD CURRENT TEAM DATA ---
    conn = sqlite3.connect(DB_PATH)
    def_df = pd.read_sql_query(f"SELECT * FROM defense WHERE Team = '{TEAM_NAME_DEF}'", conn)
    adv_df = pd.read_sql_query(f"SELECT * FROM advanced_defense WHERE Team = '{TEAM_NAME_DEF}'", conn)
    snap_df = pd.read_sql_query(f"SELECT * FROM snap_counts WHERE Team = '{TEAM_NAME_SNAP}'", conn)
    conn.close()

    # --- FILTER DEFENDERS ---
    verified_players = []
    for _, row in adv_df.iterrows():
        pos = str(row["Pos"]).strip().upper()
        player = str(row["Player"]).strip()
        group = None
        if "S" in pos:
            group = "S"
        elif "C" in pos or player.lower() == "cooper dejean":
            group = "C"
        elif "L" in pos:
            group = "L"
        elif "D" in pos and player.lower() != "cooper dejean":
            group = "D"
        if group:
            verified_players.append({"Player": player, "Pos": pos, "Group": group})

    # --- SCORE CURRENT TEAM ---
    rated = []
    rushing_scores, passing_scores, scoring_scores = [], [], []
    for player in verified_players:
        name, group = player["Player"], player["Group"]
        def_row = def_df[def_df["Player"] == name.strip()]
        adv_row = adv_df[adv_df["Player"] == name.strip()]
        snap_row = snap_df[snap_df["Player"] == name.strip()]

        if def_row.empty or adv_row.empty or snap_row.empty:
            continue

        def_row = def_row.iloc[0]
        adv_row = adv_row.iloc[0]
        snap_count = snap_row.iloc[0]["Def_Num"]

        try:
            raw_score = rate_map[group](def_row, adv_row, snap_count)
            rush = calc_rushing_impact(def_row, adv_row, group)
            pas = calc_passing_impact(def_row, adv_row, group)
            sco = calc_scoring_impact(def_row, adv_row, group)
            rushing_scores.append(rush)
            passing_scores.append(pas)
            scoring_scores.append(sco)
            rated.append({"Player": name, "Group": group, "Score": round(raw_score, 2),
                          "Rushing": rush, "Passing": pas, "Scoring": sco})
        except:
            continue

    rated_df = pd.DataFrame(rated)

    if rated_df.empty:
        continue

    # --- NORMALIZE RAW (LEAGUE-WIDE) ---
    all_scores = rated_df["Score"].tolist()
    min_score = min(all_scores)
    max_score = max(all_scores)
    rated_df["Normalized"] = rated_df["Score"].apply(lambda x: round((x - min_score) / (max_score - min_score) * 100, 2))

    # --- NORMALIZE IMPACT FIELDS (TEAM-WIDE) ---
    rated_df["Rushing"] = rated_df["Rushing"].apply(lambda x: round((x - min(rushing_scores)) / (max(rushing_scores) - min(rushing_scores)) * 100, 2) if max(rushing_scores) != min(rushing_scores) else 0)
    rated_df["Passing"] = rated_df["Passing"].apply(lambda x: round((x - min(passing_scores)) / (max(passing_scores) - min(passing_scores)) * 100, 2) if max(passing_scores) != min(passing_scores) else 0)
    rated_df["Scoring"] = rated_df["Scoring"].apply(lambda x: round((x - min(scoring_scores)) / (max(scoring_scores) - min(scoring_scores)) * 100, 2) if max(scoring_scores) != min(scoring_scores) else 0)

    # --- TEAM TOTAL RATINGS ---
    sos_dict, league_avg = strength_of_schedule.get_sos_info()
    rushing = defense.calc_rushing_defense(TEAM_ABBR, sos_dict, league_avg)
    passing = defense.calc_passing_defense(TEAM_ABBR, sos_dict, league_avg)
    scoring = defense.calc_scoring_defense(TEAM_ABBR, sos_dict, league_avg)
    total = rushing * 0.3 + passing * 0.3 + scoring * 0.4

    # --- DATABASE WRITE TO RATINGS DB ---
    ratings_conn = sqlite3.connect(RATINGS_DB_PATH)
    c = ratings_conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS player_ratings (
        player TEXT,
        pos TEXT,
        team TEXT,
        raw REAL,
        normalized REAL,
        rushing REAL,
        passing REAL,
        scoring REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS team_ratings (
        team TEXT,
        rushing REAL,
        passing REAL,
        scoring REAL,
        total REAL
    )
    """)

    for _, row in rated_df.iterrows():
        c.execute("INSERT INTO player_ratings VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            row["Player"], row["Group"], TEAM_NAME_DEF, row["Score"], row["Normalized"], row["Rushing"], row["Passing"], row["Scoring"]
        ))

    c.execute("INSERT INTO team_ratings VALUES (?, ?, ?, ?, ?)", (
        TEAM_NAME_DEF, rushing, passing, scoring, total
    ))

    ratings_conn.commit()
    ratings_conn.close()

    # --- OUTPUT ---
    print(f"\nDEFENSIVE RUNDOWN ({TEAM_ABBR})")
    print("\nTop Contributors:")
    print(rated_df.sort_values("Normalized", ascending=False).head(5))

    print("\nPositional Unit Averages:")
    print(rated_df.groupby("Group")["Normalized"].mean().round(2).reset_index())

    print("\nTeam Defense Scores:")
    print(f"Rushing: {round(rushing, 2)}")
    print(f"Passing: {round(passing, 2)}")
    print(f"Scoring: {round(scoring, 2)}")
    print(f"Total: {round(total, 2)}")

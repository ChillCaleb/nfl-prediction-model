import sqlite3
import pandas as pd
from Ratings.Offense.qb import rate_qb
from Ratings.Offense.rb import rate_rb
from Ratings.Offense.wr import rate_wr
from Ratings.Offense.te import rate_te
from Ratings.Offense.ol import rate_ol
from Engine import offense, strength_of_schedule
from Engine.constants import abbr_to_full, team_name_alias

DB_PATH = "Database/nfl_player_data.db"
RATINGS_DB_PATH = "Database/nfl_ratings.db"

sos_dict, league_avg = strength_of_schedule.get_sos_info()

for TEAM_ABBR in abbr_to_full:
    if TEAM_ABBR == "SF":
        continue

    TEAM_NAME = team_name_alias[TEAM_ABBR]
    TEAM_NAME_TITLE = TEAM_NAME.title()

    conn = sqlite3.connect(DB_PATH)
    passing = pd.read_sql_query(f"SELECT * FROM passing WHERE Team = '{TEAM_NAME}'", conn)
    adv_passing = pd.read_sql_query(f"SELECT * FROM advanced_passing WHERE Team = '{TEAM_NAME}'", conn)
    adv_rushing = pd.read_sql_query(f"SELECT * FROM advanced_rushing WHERE Team = '{TEAM_NAME}'", conn)
    receiving = pd.read_sql_query(f"SELECT * FROM advanced_receiving WHERE Team = '{TEAM_NAME}'", conn)
    combo = pd.read_sql_query(f"SELECT * FROM rushing_and_receiving WHERE Team = '{TEAM_NAME}'", conn)
    conn.close()

    rated = []
    for _, row in passing.iterrows():
        if not isinstance(row["Pos"], str) or not row["Pos"].startswith("Q"):
            continue
        adv_row = adv_passing[adv_passing["Player"] == row["Player"]]
        rush_row = adv_rushing[adv_rushing["Player"] == row["Player"]]
        if not adv_row.empty:
            score = rate_qb(row, adv_row.iloc[0], rush_row.iloc[0] if not rush_row.empty else None)
            rated.append({"Player": row["Player"], "Pos": "QB", "Score": score})

    for _, row in combo.iterrows():
        if not isinstance(row["Pos"], str) or not row["Pos"].startswith("R"):
            continue
        adv_rush_row = adv_rushing[adv_rushing["Player"] == row["Player"]]
        adv_recv_row = receiving[receiving["Player"] == row["Player"]]
        if not adv_rush_row.empty or not adv_recv_row.empty:
            score = rate_rb(row, adv_rush_row.iloc[0] if not adv_rush_row.empty else {}, adv_recv_row.iloc[0] if not adv_recv_row.empty else {})
            rated.append({"Player": row["Player"], "Pos": "RB", "Score": score})

    for _, row in receiving.iterrows():
        if not isinstance(row["Pos"], str):
            continue
        if row["Pos"].startswith("W"):
            score = rate_wr(row)
            rated.append({"Player": row["Player"], "Pos": "WR", "Score": score})
        elif row["Pos"].startswith("T"):
            score = rate_te(row)
            rated.append({"Player": row["Player"], "Pos": "TE", "Score": score})

    ol_score = rate_ol(passing, adv_rushing, combo)
    rated.append({"Player": TEAM_NAME_TITLE + " OL", "Pos": "OL", "Score": ol_score})

    df = pd.DataFrame(rated)
    if df.empty:
        continue

    min_score, max_score = df["Score"].min(), df["Score"].max()
    df["Normalized"] = df["Score"].apply(lambda x: round((x - min_score) / (max_score - min_score) * 100, 2))

    # --- TEAM OFFENSE TOTAL RATINGS ---
    rushing = offense.calc_rushing_offense(TEAM_ABBR, sos_dict, league_avg)
    passing = offense.calc_passing_offense(TEAM_ABBR, sos_dict, league_avg)
    scoring = offense.calc_scoring_offense(TEAM_ABBR, sos_dict, league_avg)
    total = rushing * 0.3 + passing * 0.3 + scoring * 0.4

    conn_out = sqlite3.connect(RATINGS_DB_PATH)
    c = conn_out.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS Offensive_player_ratings (
        player TEXT,
        pos TEXT,
        team TEXT,
        raw REAL,
        normalized REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS Offensive_team_ratings (
        team TEXT,
        rushing REAL,
        passing REAL,
        scoring REAL,
        total REAL
    )
    """)

    for _, row in df.iterrows():
        c.execute("INSERT INTO Offensive_player_ratings VALUES (?, ?, ?, ?, ?)",
                  (row["Player"], row["Pos"], TEAM_NAME, row["Score"], row["Normalized"]))

    c.execute("INSERT INTO Offensive_team_ratings VALUES (?, ?, ?, ?, ?)",
              (TEAM_NAME, rushing, passing, scoring, total))

    conn_out.commit()
    conn_out.close()

    print(f"\nOFFENSIVE RUNDOWN ({TEAM_ABBR})")
    print("\nTop Contributors:")
    print(df.sort_values("Normalized", ascending=False).head(5))

    print("\nPositional Unit Averages:")
    print(df.groupby("Pos")["Normalized"].mean().round(2).reset_index())

    print("\nTeam Offense Scores:")
    print(f"Rushing: {round(rushing, 2)}")
    print(f"Passing: {round(passing, 2)}")
    print(f"Scoring: {round(scoring, 2)}")
    print(f"Total: {round(total, 2)}")

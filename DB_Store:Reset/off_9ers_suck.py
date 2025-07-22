import sqlite3
import pandas as pd
from Ratings.Offense.qb import rate_qb
from Ratings.Offense.rb import rate_rb
from Ratings.Offense.wr import rate_wr
from Ratings.Offense.te import rate_te
from Ratings.Offense.ol import rate_ol
from Engine import offense, strength_of_schedule

# --- CONFIG ---
DB_PATH = "Database/nfl_player_data.db"
RATINGS_DB_PATH = "Database/nfl_ratings.db"

# --- GET TEAM NAME FROM 49ers PLAYER ---
conn = sqlite3.connect(DB_PATH)
team_name_row = pd.read_sql_query("""
    SELECT Team 
    FROM passing 
    WHERE Player = 'Brock Purdy' AND Pos = 'QB' AND Team = '49ers' 
    LIMIT 1
""", conn)
actual_team = team_name_row.iloc[0]["Team"]

passing = pd.read_sql_query(f"SELECT * FROM passing WHERE Team = '{actual_team}'", conn)
adv_passing = pd.read_sql_query(f"SELECT * FROM advanced_passing WHERE Team = '{actual_team}'", conn)
adv_rushing = pd.read_sql_query(f"SELECT * FROM advanced_rushing WHERE Team = '{actual_team}'", conn)
receiving = pd.read_sql_query(f"SELECT * FROM advanced_receiving WHERE Team = '{actual_team}'", conn)
combo = pd.read_sql_query(f"SELECT * FROM rushing_and_receiving WHERE Team = '{actual_team}'", conn)
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
rated.append({"Player": actual_team + " OL", "Pos": "OL", "Score": ol_score})

rated_df = pd.DataFrame(rated)
if rated_df.empty:
    raise ValueError("No rated players found for the 49ers.")

min_score = min(rated_df["Score"])
max_score = max(rated_df["Score"])
rated_df["Normalized"] = rated_df["Score"].apply(lambda x: round((x - min_score) / (max_score - min_score) * 100, 2))

# --- STORE IN DATABASE ---
ratings_conn = sqlite3.connect(RATINGS_DB_PATH)
c = ratings_conn.cursor()

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

for _, row in rated_df.iterrows():
    c.execute("INSERT INTO Offensive_player_ratings VALUES (?, ?, ?, ?, ?)", (
        row["Player"], row["Pos"], actual_team, row["Score"], row["Normalized"]
    ))

# Calculate and store team ratings using offense module
sos_dict, league_avg = strength_of_schedule.get_sos_info()
rushing = offense.calc_rushing_offense("SF", sos_dict, league_avg)
passing = offense.calc_passing_offense("SF", sos_dict, league_avg)
scoring = offense.calc_scoring_offense("SF", sos_dict, league_avg)
total = rushing * 0.3 + passing * 0.3 + scoring * 0.4

c.execute("INSERT INTO Offensive_team_ratings VALUES (?, ?, ?, ?, ?)", (
    actual_team, rushing, passing, scoring, total
))

ratings_conn.commit()
ratings_conn.close()

# --- OUTPUT ---
print("\nOFFENSIVE RUNDOWN (49ers)")
print("\nTop Contributors:")
print(rated_df.sort_values("Normalized", ascending=False).head(10))

print("\nPositional Unit Averages:")
print(rated_df.groupby("Pos")["Normalized"].mean().round(2).reset_index())

print("\nTeam Offense Scores:")
print(f"Rushing: {round(rushing, 2)}")
print(f"Passing: {round(passing, 2)}")
print(f"Scoring: {round(scoring, 2)}")
print(f"Total: {round(total, 2)}")
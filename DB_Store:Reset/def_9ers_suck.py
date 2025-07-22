import sqlite3
import pandas as pd
from Engine import defense, strength_of_schedule
from Ratings.Defense.cb import rate_cb
from Ratings.Defense.dl import rate_dl
from Ratings.Defense.lb import rate_lb
from Ratings.Defense.safety import rate_safety

# --- CONFIG ---
DB_PATH = "Database/nfl_player_data.db"
RATINGS_DB_PATH = "Database/nfl_ratings.db"

# --- GET TEAM NAME FROM FRED WARNER ---
conn = sqlite3.connect(DB_PATH)
team_name_row = pd.read_sql_query("""
    SELECT Team 
    FROM advanced_defense 
    WHERE Player = 'Fred Warner' AND Pos = 'MLB' AND Team = '49ers' 
    LIMIT 1
""", conn)
actual_team = team_name_row.iloc[0]["Team"]

def_df = pd.read_sql_query(f"SELECT * FROM defense WHERE Team = '{actual_team}'", conn)
adv_df = pd.read_sql_query(f"SELECT * FROM advanced_defense WHERE Team = '{actual_team}'", conn)
snap_df = pd.read_sql_query(f"SELECT * FROM snap_counts WHERE Team = '{actual_team}'", conn)
conn.close()

# --- FILTER DEFENDERS ---
verified_players = []
for _, row in adv_df.iterrows():
    pos = str(row["Pos"]).strip().upper()
    player = str(row["Player"]).strip()
    group = None
    if "DB" in pos or "C" in pos or player.lower() == "cooper dejean":
        group = "C"
    elif "S" in pos:
        group = "S"
    elif "L" in pos:
        group = "L"
    elif "D" in pos and player.lower() != "cooper dejean":
        group = "D"
    if group:
        verified_players.append({"Player": player, "Pos": pos, "Group": group})

# --- SCORE CURRENT TEAM ---
rated = []
rushing_scores, passing_scores, scoring_scores = [], [], []
rate_map = {'C': rate_cb, 'D': rate_dl, 'L': rate_lb, 'S': rate_safety}

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
        rush = def_row.get("Solo", 0)
        pas = def_row.get("Sk", 0) + def_row.get("Int", 0)
        sco = def_row.get("Int", 0) - adv_row.get("TD", 0)
        rushing_scores.append(rush)
        passing_scores.append(pas)
        scoring_scores.append(sco)
        rated.append({"Player": name, "Group": group, "Score": round(raw_score, 2),
                      "Rushing": rush, "Passing": pas, "Scoring": sco})
    except:
        continue

rated_df = pd.DataFrame(rated)
if rated_df.empty:
    raise ValueError("No rated players found for the 49ers.")

min_score = min(rated_df["Score"])
max_score = max(rated_df["Score"])
rated_df["Normalized"] = rated_df["Score"].apply(lambda x: round((x - min_score) / (max_score - min_score) * 100, 2))

rated_df["Rushing"] = rated_df["Rushing"].apply(lambda x: round((x - min(rushing_scores)) / (max(rushing_scores) - min(rushing_scores)) * 100, 2) if max(rushing_scores) != min(rushing_scores) else 0)
rated_df["Passing"] = rated_df["Passing"].apply(lambda x: round((x - min(passing_scores)) / (max(passing_scores) - min(passing_scores)) * 100, 2) if max(passing_scores) != min(passing_scores) else 0)
rated_df["Scoring"] = rated_df["Scoring"].apply(lambda x: round((x - min(scoring_scores)) / (max(scoring_scores) - min(scoring_scores)) * 100, 2) if max(scoring_scores) != min(scoring_scores) else 0)

# --- STORE IN DATABASE ---
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
        row["Player"], row["Group"], actual_team, row["Score"], row["Normalized"], row["Rushing"], row["Passing"], row["Scoring"]
    ))

# Calculate and store team ratings using defense module
sos_dict, league_avg = strength_of_schedule.get_sos_info()
rushing = defense.calc_rushing_defense("SF", sos_dict, league_avg)
passing = defense.calc_passing_defense("SF", sos_dict, league_avg)
scoring = defense.calc_scoring_defense("SF", sos_dict, league_avg)
total = rushing * 0.3 + passing * 0.3 + scoring * 0.4

c.execute("INSERT INTO team_ratings VALUES (?, ?, ?, ?, ?)", (
    actual_team, rushing, passing, scoring, total
))

ratings_conn.commit()
ratings_conn.close()

# --- OUTPUT ---
print("\nDEFENSIVE RUNDOWN (49ers)")
print("\nTop Contributors:")
print(rated_df.sort_values("Normalized", ascending=False).head(10))

print("\nPositional Unit Averages:")
print(rated_df.groupby("Group")["Normalized"].mean().round(2).reset_index())

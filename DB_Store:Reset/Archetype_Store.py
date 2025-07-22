import pandas as pd
import requests
import time
import os
import sys
import sqlite3
import importlib.util

spec = importlib.util.spec_from_file_location("archetype_rules", os.path.abspath("Legacy_Files/Engine/archetype_rules.py"))
archetype_rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archetype_rules)
get_archetype = archetype_rules.get_archetype

spec2 = importlib.util.spec_from_file_location("player_breakdown", os.path.abspath("Finders/player_breakdown.py"))
player_breakdown = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(player_breakdown)
get_player_blurb = player_breakdown.get_player_blurb

PLAYER_DB = "Database/nfl_player_data.db"
RATING_DB = "Database/nfl_ratings.db"

# Ensure archetype column exists
conn_check = sqlite3.connect(RATING_DB)
cursor_check = conn_check.cursor()
cursor_check.execute("PRAGMA table_info(Offensive_player_ratings);")
off_cols = [col[1] for col in cursor_check.fetchall()]
if "archetype" not in off_cols:
    cursor_check.execute("ALTER TABLE Offensive_player_ratings ADD COLUMN archetype TEXT;")
cursor_check.execute("PRAGMA table_info(Defensive_player_ratings);")
def_cols = [col[1] for col in cursor_check.fetchall()]
if "archetype" not in def_cols:
    cursor_check.execute("ALTER TABLE Defensive_player_ratings ADD COLUMN archetype TEXT;")
conn_check.commit()
conn_check.close()

def resolve_archetype(player, pos, base_dfs, adv_dfs, snap_df):
    p_lower = player.lower()
    pos = pos.upper()
    if pos == "D": pos = "DL"
    if pos == "L": pos = "LB"

    if pos == "QB":
        base, adv = base_dfs['pass'], adv_dfs['adv_pass']
    elif pos == "RB":
        base, adv = base_dfs['rushrecv'], adv_dfs['adv_rush']
    elif pos in ["WR", "TE"]:
        base, adv = base_dfs['rushrecv'], adv_dfs['adv_recv']
    else:
        base, adv = base_dfs['def'], adv_dfs['adv_def']

    base_row = base[base["Player"].str.lower() == p_lower]
    base_dict = base_row.iloc[0].to_dict() if not base_row.empty else {}
    adv_row = adv[adv["Player"].str.lower() == p_lower]
    snap_row = snap_df[snap_df["Player"].str.lower() == p_lower]

    try:
        result = get_archetype(pos, base_dict, adv_row, snap_row)
        return result["archetype"]
    except Exception:
        return "Unknown"

def store_all_archetypes():
    player_conn = sqlite3.connect(PLAYER_DB)
    rating_conn = sqlite3.connect(RATING_DB)

    base_dfs = {
        'pass': pd.read_sql("SELECT * FROM passing", player_conn),
        'rushrecv': pd.read_sql("SELECT * FROM rushing_and_receiving", player_conn),
        'def': pd.read_sql("SELECT * FROM defense", player_conn),
    }
    adv_dfs = {
        'adv_pass': pd.read_sql("SELECT * FROM advanced_passing", player_conn),
        'adv_rush': pd.read_sql("SELECT * FROM advanced_rushing", player_conn),
        'adv_recv': pd.read_sql("SELECT * FROM advanced_receiving", player_conn),
        'adv_def': pd.read_sql("SELECT * FROM advanced_defense", player_conn),
    }
    snap_df = pd.read_sql("SELECT * FROM snap_counts", player_conn)

    off_ratings = pd.read_sql("SELECT * FROM Offensive_player_ratings", rating_conn)
    def_ratings = pd.read_sql("SELECT * FROM Defensive_player_ratings", rating_conn)

    cursor = rating_conn.cursor()

    for _, row in off_ratings.iterrows():
        archetype = resolve_archetype(row["player"], row["pos"], base_dfs, adv_dfs, snap_df)
        if archetype == "Unknown":
            archetype = f"Balanced {row['pos'].upper()}"
        cursor.execute("""
            UPDATE Offensive_player_ratings SET archetype = ?
            WHERE player = ? AND team = ?
        """, (archetype, row["player"], row["team"]))

    for _, row in def_ratings.iterrows():
        archetype = resolve_archetype(row["player"], row["pos"], base_dfs, adv_dfs, snap_df)
        if archetype == "Unknown":
            archetype = f"Balanced {row['pos'].upper()}"
        cursor.execute("""
            UPDATE Defensive_player_ratings SET archetype = ?
            WHERE player = ? AND team = ?
        """, (archetype, row["player"], row["team"]))

    rating_conn.commit()
    rating_conn.close()
    player_conn.close()

if __name__ == "__main__":
    store_all_archetypes()

import sqlite3
import pandas as pd
import re
import importlib.util
import sys

# --- LOAD cb.py DYNAMICALLY ---
cb_module_path = "NFL_predict/Ratings/Defense/cb.py"
spec = importlib.util.spec_from_file_location("cb", cb_module_path)
cb = importlib.util.module_from_spec(spec)
sys.modules["cb"] = cb
spec.loader.exec_module(cb)

# --- CONNECT TO DATABASE ---
db_path = "NFL_predict/Database/nfl_player_data.db"
conn = sqlite3.connect(db_path)
def_df = pd.read_sql_query("SELECT * FROM team_broncos_defense", conn)
adv_df = pd.read_sql_query("SELECT * FROM team_broncos_advanced_defense", conn)
snap_df = pd.read_sql_query("SELECT * FROM team_broncos_snaps", conn)
conn.close()

# --- CLEAN COLUMN NAMES IN DEFENSE TABLE ---
def_df.columns = [
    re.sub(r"^\('.*?', '(.*?)'\)$", r"\1", col) if isinstance(col, str) else col
    for col in def_df.columns
]

# --- FILTER CORNERBACKS ---
def_pos_col = next(col for col in def_df.columns if "Pos" in col)
cb_def_df = def_df[def_df[def_pos_col].astype(str).str.contains("CB", case=False, na=False)]
cb_adv_df = adv_df[adv_df["Pos"].astype(str).str.contains("CB", case=False, na=False)]

# --- FILTER SNAP COUNTS ---
snap_clean = snap_df.iloc[1:].copy()
cb_snap_df = snap_clean[snap_clean["Unnamed: 1_level_0"].astype(str).str.contains("CB", case=False, na=False)]

# --- RENAME FOR JOINING ---
cb_def_df = cb_def_df.rename(columns={next(c for c in cb_def_df.columns if "Player" in c): "Player"})
cb_adv_df = cb_adv_df.rename(columns={"Player": "Player"})
cb_snap_df = cb_snap_df.rename(columns={"Unnamed: 0_level_0": "Player"})

# --- COMPUTE RATINGS ---
ratings = []
for _, def_row in cb_def_df.iterrows():
    name = def_row["Player"]
    adv_row = cb_adv_df[cb_adv_df["Player"] == name]
    snap_row = cb_snap_df[cb_snap_df["Player"] == name]

    snap_count = float(snap_row["Def."].values[0]) if not snap_row.empty else 0
    tgt = float(adv_row["Tgt"].values[0]) if not adv_row.empty else 0
    target_rate = (tgt / snap_count) * 100 if snap_count > 0 else 100

    rating = cb.rate_cb(def_row, adv_row=adv_row, snap_count=snap_count, target_rate=target_rate)
    ratings.append({"Player": name, "Rating": rating})

# --- DISPLAY RESULTS ---
ratings_df = pd.DataFrame(ratings).sort_values(by="Rating", ascending=False)
print("\n--- BRONCOS CORNERBACK RATINGS ---\n")
print(ratings_df.to_string(index=False))

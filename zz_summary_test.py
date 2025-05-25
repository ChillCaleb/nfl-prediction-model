import sqlite3
import pandas as pd
import re
import importlib

team = input("Enter team name (e.g. lions, eagles): ").strip().lower()
positions = ["CB", "S", "LB", "DL"]
summary = {}

def_db = f"Database/nfl_player_data.db"
conn = sqlite3.connect(def_db)

for position in positions:
    def_df = pd.read_sql_query(f"SELECT * FROM team_{team}_defense", conn)
    adv_df = pd.read_sql_query(f"SELECT * FROM team_{team}_advanced_defense", conn)
    try:
        snap_df = pd.read_sql_query(f"SELECT * FROM team_{team}_snaps", conn)
        snap_clean = snap_df.iloc[1:].copy()
    except:
        snap_clean = pd.DataFrame(columns=["Player", "Unnamed: 1_level_0", "Def."])

    def_df.columns = [re.sub(r"^\('.*?', '(.*?)'\)$", r"\1", col) if isinstance(col, str) else col for col in def_df.columns]
    pos_col = next(col for col in def_df.columns if "Pos" in col)

    DL_ALIASES = ["DL", "DE", "DT", "EDGE", "NT", "RDE", "LDE"]
    if position == "DL":
        def_filtered = def_df[def_df[pos_col].astype(str).str.upper().apply(lambda val: any(alias in val for alias in DL_ALIASES))]
        adv_filtered = adv_df[adv_df["Pos"].astype(str).str.upper().apply(lambda val: any(alias in val for alias in DL_ALIASES))]
        snap_filtered = snap_clean[snap_clean["Unnamed: 1_level_0"].astype(str).str.upper().apply(lambda val: any(alias in val for alias in DL_ALIASES))]
    else:
        def_filtered = def_df[def_df[pos_col].astype(str).str.contains(position, case=False, na=False)]
        adv_filtered = adv_df[adv_df["Pos"].astype(str).str.contains(position, case=False, na=False)]
        snap_filtered = snap_clean[snap_clean["Unnamed: 1_level_0"].astype(str).str.contains(position, case=False, na=False)]

    def_filtered = def_filtered.rename(columns={next(c for c in def_filtered.columns if "Player" in c): "Player"})
    adv_filtered = adv_filtered.rename(columns={"Player": "Player"})
    snap_filtered = snap_filtered.rename(columns={"Unnamed: 0_level_0": "Player"})

    ratings = []
    for _, row in def_filtered.iterrows():
        name = row["Player"]
        adv_row = adv_filtered[adv_filtered["Player"] == name]
        snap_row = snap_filtered[snap_filtered["Player"] == name]

        snap_count = float(snap_row["Def."].values[0]) if not snap_row.empty else None
        tgt = float(adv_row["Tgt"].values[0]) if not adv_row.empty else 0

        row["Tgt"] = tgt
        row["def_num"] = snap_count if snap_count is not None else 0
        row["target_rate"] = (tgt / snap_count * 100) if snap_count else 0

        if position == "CB":
            mod = importlib.import_module("Ratings.Defense.cb")
            score = mod.rate_cb(row, verbose=False)
        elif position == "S":
            mod = importlib.import_module("Ratings.Defense.safety")
            score = mod.rate_safety(row, adv_row=adv_row.iloc[0] if not adv_row.empty else None, snap_count=snap_count, verbose=False)
        elif position == "LB":
            mod = importlib.import_module("Ratings.Defense.lb")
            score = mod.rate_lb(row, adv_row=adv_row.iloc[0] if not adv_row.empty else None, snap_count=snap_count, verbose=False)
        elif position == "DL":
            mod = importlib.import_module("Ratings.Defense.dl")
            score = mod.rate_dl(row, adv_row=adv_row.iloc[0] if not adv_row.empty else None, snap_count=snap_count, targets=tgt, verbose=False)
        else:
            score = 0

        ratings.append(score)

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0

    if position == "DL":
        sacks = def_filtered["Sk"].sum() if "Sk" in def_filtered else 0
        summary[position] = f"{position}: {sacks} Sacks | Avg Rating: {avg_rating}"
    elif position == "LB":
        tackles = def_filtered["Comb"].sum() if "Comb" in def_filtered else 0
        summary[position] = f"{position}: {tackles} Tackles | Avg Rating: {avg_rating}"
    elif position in ["CB", "S"]:
        int_total = def_filtered["Int"].sum() if "Int" in def_filtered else 0
        tgt_total = adv_filtered["Tgt"].sum() if "Tgt" in adv_filtered else 0
        snap_total = snap_filtered["Def."].sum() if "Def." in snap_filtered else 0
        tgt_rate = (tgt_total / snap_total * 100) if snap_total else 0
        summary[position] = f"{position}: {int_total} INT, {tgt_rate:.1f}% Target Rate | Avg Rating: {avg_rating}"

conn.close()

print(f"\n--- {team.upper()} DEFENSIVE UNIT SUMMARY ---")
for pos in positions:
    print(summary.get(pos, f"{pos}: No data available"))

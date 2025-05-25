import sqlite3
import pandas as pd
import re
import importlib

# --- USER INPUT PROMPT ---
team = input("Enter team name (e.g. broncos, bills, eagles): ").strip().lower()
position = input("Enter position code (e.g. CB, S, LB): ").strip().upper()

# --- DISPATCHER FUNCTION (INLINE) ---
def rate_player_by_inferred_position(row, adv_row, snap_count, tgt, verbose=False):
    position = str(row.get("Pos", "")).upper()

    if any(x in position for x in ["DL", "DE", "DT", "EDGE", "NT", "RDE", "LDE"]):
        position = "DL"

    if "CB" in position:
        mod = importlib.import_module("Ratings.Defense.cb")
        return mod.rate_cb(row, verbose=verbose)

    elif "LB" in position:
        mod = importlib.import_module("Ratings.Defense.lb")
        return mod.rate_lb(row, adv_row=adv_row.iloc[0] if not adv_row.empty else None, snap_count=snap_count, verbose=verbose)

    elif "DL" in position:
        mod = importlib.import_module("Ratings.Defense.dl")
        return mod.rate_dl(
            dl_row=row,
            adv_row=adv_row.iloc[0] if not adv_row.empty else None,
            snap_count=snap_count,
            targets=tgt,
            completions=adv_row["Cmp"].values[0] if not adv_row.empty and "Cmp" in adv_row else None,
            tfl=adv_row["TFL"].values[0] if not adv_row.empty and "TFL" in adv_row else None,
            verbose=verbose
        )

    elif "S" in position:
        mod = importlib.import_module("Ratings.Defense.safety")
        return mod.rate_safety(row, adv_row=adv_row.iloc[0] if not adv_row.empty else None, snap_count=snap_count, verbose=verbose)

    else:
        if verbose:
            print(f"⚠️ No rating function found for position: {position}")
        return 0.0

# --- LOAD DATA FROM DATABASE ---
db_path = "Database/nfl_player_data.db"
conn = sqlite3.connect(db_path)
def_df = pd.read_sql_query(f"SELECT * FROM team_{team}_defense", conn)
adv_df = pd.read_sql_query(f"SELECT * FROM team_{team}_advanced_defense", conn)
try:
    snap_df = pd.read_sql_query(f"SELECT * FROM team_{team}_snaps", conn)
    snap_clean = snap_df.iloc[1:].copy()
except Exception as e:
    print(f"⚠️ No snap data available for {team}. Defaulting snap counts to 0.")
    snap_clean = pd.DataFrame(columns=["Player", "Unnamed: 1_level_0", "Def."])
conn.close()

# --- CLEAN COLUMN NAMES IN DEFENSE TABLE ---
def_df.columns = [
    re.sub(r"^\('.*?', '(.*?)'\)$", r"\1", col) if isinstance(col, str) else col
    for col in def_df.columns
]

# --- FILTER BY POSITION ---
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

# --- NORMALIZE PLAYER COLUMN ---
def_filtered = def_filtered.rename(columns={next(c for c in def_filtered.columns if "Player" in c): "Player"})
adv_filtered = adv_filtered.rename(columns={"Player": "Player"})
snap_filtered = snap_filtered.rename(columns={"Unnamed: 0_level_0": "Player"})

# --- CALCULATE RATINGS ---
ratings = []
print(f"🧪 {len(def_filtered)} players matched for {team} {position}")
print(def_filtered["Player"].tolist())
for _, row in def_filtered.iterrows():
    name = row["Player"]
    adv_row = adv_filtered[adv_filtered["Player"] == name]
    snap_row = snap_filtered[snap_filtered["Player"] == name]

    snap_count = float(snap_row["Def."].values[0]) if not snap_row.empty else None
    tgt = float(adv_row["Tgt"].values[0]) if not adv_row.empty else 0
    target_rate = (tgt / snap_count) * 100 if snap_count else 100

    # Inject derived values into row
    row["Tgt"] = tgt
    row["def_num"] = snap_count if snap_count is not None else 0
    row["target_rate"] = target_rate

    score = rate_player_by_inferred_position(row, adv_row, snap_count, tgt, verbose=False)
    if score is None:
        print(f"⚠️ {name} returned no score!")
    ratings.append({"Player": name, "Rating": score})

# --- DISPLAY RESULTS ---
if ratings:
    ratings_df = pd.DataFrame(ratings).sort_values(by="Rating", ascending=False)
    print(f"\n--- {team.upper()} {position.upper()} RATINGS ---\n")
    print(ratings_df.to_string(index=False))

    # --- DEFENSIVE UNIT SUMMARY ---
    pass_tgt = adv_filtered["Tgt"].sum() if "Tgt" in adv_filtered else 0
    pass_cmp = adv_filtered["Cmp"].sum() if "Cmp" in adv_filtered else 0
    pass_pct = (pass_cmp / pass_tgt * 100) if pass_tgt > 0 else 0
    total_int = def_filtered["Int"].sum() if "Int" in def_filtered else 0
    total_pd = def_filtered["PD"].sum() if "PD" in def_filtered else 0

    total_tfl = def_filtered["TFL"].sum() if "TFL" in def_filtered else 0
    total_comb = def_filtered["Comb"].sum() if "Comb" in def_filtered else 0
    total_mtkl = def_filtered["MTkl"].sum() if "MTkl" in def_filtered else 0

    print("\n--- {} {} SUMMARY ---".format(team.upper(), position.upper()))
    print("Passing Defense: {} Tgt, {} Cmp, {:.1f}% Comp, {} INT, {} PD".format(
        int(pass_tgt), int(pass_cmp), pass_pct, int(total_int), int(total_pd)))
    print("Rushing Defense: {} Tackles, {} TFL, {} Missed Tackles".format(
        int(total_comb), int(total_tfl), int(total_mtkl)))
else:
    print(f"⚠️ No ratings available for {team} {position}. Check filters or input.")
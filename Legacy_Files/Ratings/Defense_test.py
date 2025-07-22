import sqlite3
import pandas as pd
from Ratings.Defense.cb import rate_cb
from Ratings.Defense.dl import rate_dl
from Ratings.Defense.lb import rate_lb
from Ratings.Defense.safety import rate_safety

def safe_match(name, df, key="Player"):
    return df[df[key].str.lower().str.strip() == name.lower().strip()]

def run_defense_profile(team, db_path):
    conn = sqlite3.connect(db_path)
    try:
        defense_df = pd.read_sql_query("SELECT * FROM defense WHERE LOWER(Team) = ?", conn, params=[team])
        adv_def_df = pd.read_sql_query("SELECT * FROM advanced_defense WHERE LOWER(Team) = ?", conn, params=[team])
        snap_df = pd.read_sql_query("SELECT * FROM snap_counts WHERE LOWER(Team) = ?", conn, params=[team])

        player_col = "Player"
        pos_col = "Pos"

        # --- Defensive Line (best DL)
        dl_keywords = ["DL", "DE", "DT", "NT", "RDE", "LDE", "RDT", "LDT"]
        is_dl = defense_df[pos_col].astype(str).apply(lambda x: any(k in x for k in dl_keywords))
        dl_df = defense_df[is_dl]
        dl_ratings = []
        for _, row in dl_df.iterrows():
            adv_row = safe_match(row[player_col], adv_def_df)
            if not adv_row.empty:
                rating = rate_dl(row, adv_row.iloc[0], verbose=False)
                dl_ratings.append((row[player_col], rating))
        dl_ratings.sort(key=lambda x: x[1], reverse=True)
        dl_name, dl_rating = dl_ratings[0] if dl_ratings else ("", 0.0)
        if dl_name:
            top_dl_row = safe_match(dl_name, dl_df).iloc[0]
            top_dl_adv = safe_match(dl_name, adv_def_df).iloc[0]
            rate_dl(top_dl_row, top_dl_adv, verbose=True)

        # --- Linebacker
        lb_df = defense_df[defense_df[pos_col].str.contains("LB", na=False)]
        lb_row = lb_df.iloc[0] if not lb_df.empty else None
        adv_lb = safe_match(lb_row[player_col], adv_def_df) if lb_row is not None else pd.DataFrame()
        lb_name = lb_row[player_col] if lb_row is not None else ""
        lb_rating = rate_lb(lb_row, adv_lb.iloc[0], verbose=True) if not adv_lb.empty else 0.0

        # --- Safety
        s_df = defense_df[defense_df[pos_col].str.contains("S", na=False)]
        s_row = s_df.iloc[0] if not s_df.empty else None
        adv_s = safe_match(s_row[player_col], adv_def_df) if s_row is not None else pd.DataFrame()
        s_name = s_row[player_col] if s_row is not None else ""
        s_rating = rate_safety(s_row, adv_s.iloc[0], verbose=True) if not adv_s.empty else 0.0

        # --- Cornerbacks
        cb_df = defense_df[defense_df[pos_col].str.contains("CB", na=False)]
        cb_ratings = []
        for _, row in cb_df.iterrows():
            adv_row = safe_match(row[player_col], adv_def_df)
            snap_row = safe_match(row[player_col], snap_df)
            snap_count = int(snap_row["Def_Num"].values[0]) if not snap_row.empty else 0
            if not adv_row.empty:
                try:
                    rating = rate_cb(row, adv_row.iloc[0], snap_count=snap_count, verbose=False)
                    cb_ratings.append((row[player_col], rating))
                except:
                    continue
        cb_ratings.sort(key=lambda x: x[1], reverse=True)
        cb_name, cb_rating = cb_ratings[0] if cb_ratings else ("", 0.0)
        if cb_name:
            top_cb_row = safe_match(cb_name, cb_df).iloc[0]
            top_cb_adv = safe_match(cb_name, adv_def_df).iloc[0]
            top_cb_snap = safe_match(cb_name, snap_df)
            snap_count = int(top_cb_snap["Def_Num"].values[0]) if not top_cb_snap.empty else 0
            rate_cb(top_cb_row, top_cb_adv, snap_count=snap_count, verbose=True)

        print("\n📊 CALCULATING UNIT RATINGS")
        print(f"DL: {dl_rating}")
        print(f"LB: {lb_rating}")
        print(f"CB: {cb_rating}")
        print(f"S:  {s_rating}")

        overall = round((dl_rating + lb_rating + cb_rating + s_rating) / 4, 2)

        print("\n📈 SCORING, RUN, PASS BREAKDOWN")
        scoring_def = round(0.20 * dl_rating + 0.20 * lb_rating + 0.30 * cb_rating + 0.30 * s_rating, 2)
        run_def = round(0.45 * dl_rating + 0.35 * lb_rating + 0.10 * cb_rating + 0.10 * s_rating, 2)
        pass_def = round(0.15 * dl_rating + 0.20 * lb_rating + 0.35 * cb_rating + 0.30 * s_rating, 2)

        print(f"Scoring Defense: {scoring_def}")
        print(f"Run Defense: {run_def}")
        print(f"Pass Defense: {pass_def}")
        print(f"Overall Defense: {overall}")

        print("\n🏆 Top 3 Defensive Contributors:")
        top_3 = sorted([
            (dl_name, "DL", dl_rating),
            (lb_name, "LB", lb_rating),
            (cb_name, "CB", cb_rating),
            (s_name, "S", s_rating)
        ], key=lambda x: x[2], reverse=True)[:3]
        for name, position, score in top_3:
            print(f"{name} ({position}): {score}")

        return {
            "team": team,
            "overall": overall,
            "ratings": {
                "DL": dl_rating,
                "LB": lb_rating,
                "CB": cb_rating,
                "S": s_rating,
                "scoring_defense": scoring_def,
                "run_defense": run_def,
                "pass_defense": pass_def
            }
        }

    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "Database/nfl_player_data.db"
    team = input("Enter team (e.g. 'ravens'): ").strip().lower()
    run_defense_profile(team, db_path)
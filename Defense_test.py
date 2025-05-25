import sqlite3
import pandas as pd
import os
import traceback
from Ratings.Defense.dl import rate_dl
from Ratings.Defense.lb import rate_lb
from Ratings.Defense.cb import rate_cb
from Ratings.Defense.safety import rate_safety

def calculate_defensive_profile(team, db_path):
    conn = sqlite3.connect(db_path)
    try:
        p = lambda tbl: pd.read_sql_query(f"SELECT * FROM team_{team}_{tbl};", conn)
        defense_df = p("defense")
        adv_def_df = p("advanced_defense")
        snap_count_df = p("snaps")


        defense_df = defense_df.fillna(0)
        adv_def_df = adv_def_df.fillna(0)
        snap_count_df = snap_count_df.fillna(0)

        # Dynamically locate 'Player' and 'Pos' columns
        player_col = next((col for col in defense_df.columns if "player" in str(col).lower()), None)
        pos_col = next((col for col in defense_df.columns if "pos" in str(col).lower()), None)

        if player_col is None or pos_col is None:
            raise KeyError("Could not locate 'Player' or 'Pos' column in defense table.")

        # Extract player names by position
        dl_name = defense_df[defense_df[pos_col].str.contains("DL|DE|DT|NT|EDGE", na=False)].iloc[0][player_col]
        lb_name = defense_df[defense_df[pos_col].str.contains("LB", na=False)].iloc[0][player_col]
        s_name  = defense_df[defense_df[pos_col].str.contains("S", na=False)].iloc[0][player_col]

        dl_row = defense_df[defense_df[player_col] == dl_name].iloc[0]
        lb_row = defense_df[defense_df[player_col] == lb_name].iloc[0]

        s_row  = defense_df[defense_df[player_col] == s_name].iloc[0]
        

        adv_dl_row = adv_def_df[adv_def_df["Player"] == dl_name].iloc[0]
        adv_lb_row = adv_def_df[adv_def_df["Player"] == lb_name].iloc[0]
        adv_s_row  = adv_def_df[adv_def_df["Player"] == s_name].iloc[0]


#====================Snap Count=========================
        # Load snap count table from DB
        snap_count_df = pd.read_sql_query(f"SELECT * FROM team_{team}_snaps;", conn)

        # Skip the label row
        snap_count_df = snap_count_df.iloc[1:].reset_index(drop=True)

        # Rename known useful columns manually
        snap_count_df.rename(columns={
            "Unnamed: 0_level_0": "player",
            "Def.": "def_num"
        }, inplace=True)

        # Match the player name exactly

        # Get snap count
        print("📋 Available players in snap table:")
        print(snap_count_df["player"].head(10).tolist())

        print("✅ Match found!")
        else:
            print("❌ No match found.")


#======================Cornereback=========================
        # CB Rating
        cb_ratings = []

        # Normalize and rename snap_count_df columns
        snap_count_df.columns = [str(c).strip().lower() for c in snap_count_df.columns]
        if "player" not in snap_count_df.columns:
            for col in snap_count_df.columns:
                if "player" in col:
                    snap_count_df.rename(columns={col: "player"}, inplace=True)
                    break
        if "def. num" not in snap_count_df.columns:
            for col in snap_count_df.columns:
                if "def" in col and "num" in col:
                    snap_count_df.rename(columns={col: "def. num"}, inplace=True)
                    break

        for _, cb_row in cb_rows.iterrows():
            try:
                cb_name = cb_row[player_col]
                adv_row = adv_def_df[adv_def_df["Player"] == cb_name]
                if adv_row.empty:
                    continue

                snap_row = snap_count_df[snap_count_df["player"].str.lower().str.strip() == cb_name.lower().strip()]
                snap_count = int(snap_row["def. num"].values[0]) if not snap_row.empty else 0

                rating = rate_cb(cb_row, adv_row.iloc[0], snap_count=snap_count, verbose=True)
                cb_ratings.append(rating)
            except Exception as e:
                print(f"[CB ERROR] {e}")
                continue

        cb_rating = round(sum(cb_ratings) / len(cb_ratings), 2) if cb_ratings else 0.0
        cb_ratings = []

        # Normalize snap_count_df columns
        snap_count_df.columns = [c.strip().lower() for c in snap_count_df.columns]
        if "player" not in snap_count_df.columns:
            for col in snap_count_df.columns:
                if "player" in col:
                    snap_count_df.rename(columns={col: "player"}, inplace=True)
                    break
        if "def. num" not in snap_count_df.columns:
            for col in snap_count_df.columns:
                if "def" in col and "num" in col:
                    snap_count_df.rename(columns={col: "def. num"}, inplace=True)
                    break

            try:
                if adv_row.empty:
                    continue

                snap_count = int(snap_row["def. num"].values[0]) if not snap_row.empty else 0

                rating = rate_cb(row, adv_row.iloc[0], snap_count=snap_count, verbose=True)
                cb_ratings.append(rating)
            except Exception as e:
                print(f"[CB ERROR] {e}")
                continue

        cb_rating = round(sum(cb_ratings) / len(cb_ratings), 2) if cb_ratings else 0.0

#======================Results=========================
        print("\n📊 CALCULATING UNIT RATINGS\n")
        dl_rating = rate_dl(dl_row, adv_dl_row)
        lb_rating = rate_lb(lb_row, adv_lb_row)
        s_rating  = rate_safety(s_row, adv_s_row)

        print("\n🔢 POSITIONAL RATINGS")
        print(f"DL: {dl_rating}")
        print(f"LB: {lb_rating}")
        print(f"CB: {cb_rating}")
        print(f"S:  {s_rating}")

        overall = round((dl_rating + lb_rating + cb_rating + s_rating) / 4, 2)

        print("\n🏁 FINAL DEFENSIVE PROFILE")
        print(f"Overall Defense: {overall}")

        globals().update({
            'dl_name': dl_name,
            'lb_name': lb_name,
            's_name': s_name,
            'dl_rating': dl_rating,
            'lb_rating': lb_rating,
            'cb_rating': cb_rating,
            's_rating': s_rating
        })

        return {
            "overall": overall
        }



    except Exception:
        print("[DEFENSE ERROR]")
        traceback.print_exc()
        return {}


    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "Database/nfl_player_data.db"
    team = input("Enter team (e.g. 'lions'): ").strip().lower()
    calculate_defensive_profile(team, db_path)


# --- Top 3 Defensive Contributors ---
try:
    contributions = [
        (dl_name, "DL", dl_rating),
        (lb_name, "LB", lb_rating),
        (s_name, "S", s_rating)
    ]

    top_3_defense = sorted(contributions, key=lambda x: x[2], reverse=True)[:3]

    print("\nTop 3 Defensive Contributors:")
    for name, position, score in top_3_defense:
        print(f"{name} ({position}): {score}")
except NameError:
    print("\u26a0\ufe0f Warning: Positional ratings not available in global scope. Run the main function first.")
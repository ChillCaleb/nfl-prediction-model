import sqlite3
import pandas as pd
import os
from Ratings.Offense.qb import rate_qb
from Ratings.Offense.rb import rate_rb
from Ratings.Offense.wr import rate_wr
from Ratings.Offense.te import rate_te
from Ratings.Offense.ol import rate_ol

def calculate_scoring_offense(qb, rb, ol, wr1, wr2, te):
    return round(
        0.30 * qb +
        0.35 * ol +
        0.15 * rb +
        0.10 * wr1 +
        0.05 * wr2 +
        0.05 * te,
        2
    )

def calculate_rushing_offense(ol, rb, qb_rush):
    return round(
        0.50 * ol +
        0.35 * rb +
        0.15 * qb_rush,
        2
    )

def calculate_passing_offense(qb, ol, wr1, wr2, te):
    return round(
        0.30 * qb +
        0.30 * (0.5 * ol) +
        0.15 * wr1 +
        0.10 * wr2 +
        0.15 * te,
        2
    )

def calculate_offensive_profile(team, db_path):
    conn = sqlite3.connect(db_path)
    try:
        p = lambda tbl: pd.read_sql_query(f"SELECT * FROM team_{team}_{tbl};", conn)
        passing_df = p("passing")
        adv_pass_df = p("advanced_passing")
        adv_rush_df = p("advanced_rushing")
        combo_df = p("rushing_and_receiving")
        adv_recv_df = p("advanced_receiving")

        qb_name = passing_df.iloc[0]["Player"]
        rb_name = adv_rush_df[adv_rush_df["Pos"] == "RB"].iloc[0]["Player"]
        wr_df = adv_recv_df[adv_recv_df["Pos"] == "WR"]
        te_df = adv_recv_df[adv_recv_df["Pos"] == "TE"]
        wr1_name = wr_df.iloc[0]["Player"]
        wr2_name = wr_df.iloc[1]["Player"] if len(wr_df) > 1 else wr_df.iloc[0]["Player"]
        te_name = te_df.iloc[0]["Player"] if not te_df.empty else wr1_name

        p_row = passing_df[passing_df["Player"] == qb_name].iloc[0]
        ap_row = adv_pass_df[adv_pass_df["Player"] == qb_name].iloc[0]
        rush_row = adv_rush_df[adv_rush_df["Player"] == qb_name].iloc[0]

        player_col = [col for col in combo_df.columns if "Player" in col][0]
        combo_row = combo_df[combo_df[player_col].astype(str).str.contains(rb_name, case=False, na=False)].iloc[0]

        rb_rush_row = adv_rush_df[adv_rush_df["Player"] == rb_name].iloc[0]
        rb_recv_row = adv_recv_df[adv_recv_df["Player"] == rb_name].iloc[0]
        wr1_row = adv_recv_df[adv_recv_df["Player"] == wr1_name].iloc[0]
        wr2_row = adv_recv_df[adv_recv_df["Player"] == wr2_name].iloc[0]
        te_row = adv_recv_df[adv_recv_df["Player"] == te_name].iloc[0]

        print("\n📊 CALCULATING UNIT RATINGS\n")
        qb_rating = rate_qb(p_row, ap_row, rush_row)
        rb_rating = rate_rb(combo_row, rb_rush_row, rb_recv_row)
        wr1_rating = rate_wr(wr1_row)
        wr2_rating = rate_wr(wr2_row)
        te_rating = rate_te(te_row)
        ol_rating = rate_ol(passing_df, adv_rush_df, combo_df)

        print("\n🔢 POSITIONAL RATINGS")
        print(f"QB:  {qb_rating}")
        print(f"RB:  {rb_rating}")
        print(f"WR1: {wr1_rating}")
        print(f"WR2: {wr2_rating}")
        print(f"TE:  {te_rating}")
        print(f"OL:  {ol_rating}")

        qb_rush_rating = max(rate_qb(p_row, ap_row, rush_row) - rate_qb(p_row, ap_row, None), 0)
        qb_pass_rating = rate_qb(p_row, ap_row, None)

        print("\n📈 SCORING, RUSHING, PASSING BREAKDOWN\n")
        scoring = calculate_scoring_offense(qb_rating, rb_rating, ol_rating, wr1_rating, wr2_rating, te_rating)
        rushing = calculate_rushing_offense(ol_rating, rb_rating, qb_rush_rating)
        passing = calculate_passing_offense(qb_pass_rating, ol_rating, wr1_rating, wr2_rating, te_rating)

        overall = round(0.5 * scoring + 0.25 * rushing + 0.25 * passing, 2)

        print("\n🏁 FINAL OFFENSIVE PROFILE")
        print(f"Scoring Offense: {scoring}")
        print(f"Rushing Offense: {rushing}")
        print(f"Passing Offense: {passing}")
        print(f"Overall Offense: {overall}")

        # Make values globally accessible
        globals().update({
            'qb_name': qb_name,
            'rb_name': rb_name,
            'wr1_name': wr1_name,
            'wr2_name': wr2_name,
            'te_name': te_name,
            'ol_rating': ol_rating,
            'qb_rating': qb_rating,
            'rb_rating': rb_rating,
            'wr1_rating': wr1_rating,
            'wr2_rating': wr2_rating,
            'te_rating': te_rating
        })

        return {
            "scoring": scoring,
            "rushing": rushing,
            "passing": passing,
            "overall": overall
        }

    except Exception as e:
        print(f"[OFFENSE ERROR] {e}")
        return {}
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = "Database/nfl_player_data.db"
    team = input("Enter team (e.g. 'lions'): ").strip().lower()
    calculate_offensive_profile(team, db_path)
# --- Top 3 Offensive Contributors ---
try:
    contributions = [
        (qb_name, "QB", qb_rating),
        (rb_name, "RB", rb_rating),
        (wr1_name, "WR1", wr1_rating),
        (wr2_name, "WR2", wr2_rating),
        (te_name, "TE", te_rating),
        ("Offensive Line", "OL", ol_rating)
    ]

    top_3_offense = sorted(contributions, key=lambda x: x[2], reverse=True)[:3]

    print("\nTop 3 Offensive Contributors:")
    for name, position, score in top_3_offense:
        print(f"{name} ({position}): {score}")
except NameError:
    print("⚠️ Warning: Positional ratings not available in global scope. Run the main function first.")

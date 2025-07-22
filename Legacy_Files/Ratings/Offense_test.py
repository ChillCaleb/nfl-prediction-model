import sqlite3
import pandas as pd
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
        0.15 * ol +
        0.15 * wr1 +
        0.10 * wr2 +
        0.15 * te,
        2
    )

def calculate_offensive_profile(team, db_path, verbose=True):
    conn = sqlite3.connect(db_path)
    try:
        team_lower = team.lower()

        passing_df = pd.read_sql_query("SELECT * FROM passing WHERE LOWER(Team) = ?", conn, params=[team_lower])
        adv_pass_df = pd.read_sql_query("SELECT * FROM advanced_passing WHERE LOWER(Team) = ?", conn, params=[team_lower])
        adv_rush_df = pd.read_sql_query("SELECT * FROM advanced_rushing WHERE LOWER(Team) = ?", conn, params=[team_lower])
        combo_df = pd.read_sql_query("SELECT * FROM rushing_and_receiving WHERE LOWER(Team) = ?", conn, params=[team_lower])
        adv_recv_df = pd.read_sql_query("SELECT * FROM advanced_receiving WHERE LOWER(Team) = ?", conn, params=[team_lower])

        qb_name = passing_df.iloc[0]["Player"]
        rb_name = adv_rush_df[adv_rush_df["Pos"] == "RB"].iloc[0]["Player"]

        wr_df = adv_recv_df[adv_recv_df["Pos"] == "WR"]
        te_df = adv_recv_df[adv_recv_df["Pos"] == "TE"]
        wr1_name = wr_df.iloc[0]["Player"]
        wr2_name = wr_df.iloc[1]["Player"] if len(wr_df) > 1 else wr1_name
        te_name = te_df.iloc[0]["Player"] if not te_df.empty else wr1_name

        p_row = passing_df[passing_df["Player"] == qb_name].iloc[0]
        ap_row = adv_pass_df[adv_pass_df["Player"] == qb_name].iloc[0]
        rush_row = adv_rush_df[adv_rush_df["Player"] == qb_name].iloc[0]

        player_col = [col for col in combo_df.columns if "Player" in col][0]
        combo_row = combo_df[combo_df[player_col].str.contains(rb_name, case=False, na=False)].iloc[0]

        rb_rush_row = adv_rush_df[adv_rush_df["Player"] == rb_name].iloc[0]
        rb_recv_row = adv_recv_df[adv_recv_df["Player"] == rb_name].iloc[0]
        wr1_row = adv_recv_df[adv_recv_df["Player"] == wr1_name].iloc[0]
        wr2_row = adv_recv_df[adv_recv_df["Player"] == wr2_name].iloc[0]
        te_row = adv_recv_df[adv_recv_df["Player"] == te_name].iloc[0]

        # Ratings
        qb_full = rate_qb(p_row, ap_row, rush_row)
        qb_pass = rate_qb(p_row, ap_row, None)
        qb_rush = max(qb_full - qb_pass, 0)

        rb_rating = rate_rb(combo_row, rb_rush_row, rb_recv_row)
        wr1_rating = rate_wr(wr1_row)
        wr2_rating = rate_wr(wr2_row)
        te_rating = rate_te(te_row)
        ol_rating = rate_ol(passing_df, adv_rush_df, combo_df)

        if verbose:
            print("\n📊 CALCULATING UNIT RATINGS")
            print(f"QB:  {qb_pass}")
            print(f"RB:  {rb_rating}")
            print(f"WR1: {wr1_rating}")
            print(f"WR2: {wr2_rating}")
            print(f"TE:  {te_rating}")
            print(f"OL:  {ol_rating}")

        scoring = calculate_scoring_offense(qb_pass, rb_rating, ol_rating, wr1_rating, wr2_rating, te_rating)
        rushing = calculate_rushing_offense(ol_rating, rb_rating, qb_rush)
        passing = calculate_passing_offense(qb_pass, ol_rating, wr1_rating, wr2_rating, te_rating)
        overall = round(0.5 * scoring + 0.25 * rushing + 0.25 * passing, 2)

        if verbose:
            print("\n📈 SCORING, RUSHING, PASSING BREAKDOWN")
            print(f"Scoring Offense: {scoring}")
            print(f"Rushing Offense: {rushing}")
            print(f"Passing Offense: {passing}")
            print(f"Overall Offense: {overall}")

        return {
            "team": team,
            "qb": qb_name, "rb": rb_name, "wr1": wr1_name, "wr2": wr2_name, "te": te_name,
            "ratings": {
                "QB": qb_pass, "RB": rb_rating, "WR1": wr1_rating,
                "WR2": wr2_rating, "TE": te_rating, "OL": ol_rating
            },
            "breakdown": {
                "scoring": scoring,
                "rushing": rushing,
                "passing": passing,
                "overall": overall
            }
        }

    except Exception as e:
        print(f"[OFFENSE ERROR] {e}")
        return {}
    finally:
        conn.close()


if __name__ == "__main__":
    team = input("Enter team (e.g. 'lions'): ").strip()
    db_path = "Database/nfl_player_data.db"
    result = calculate_offensive_profile(team, db_path)

    if result:
        # Use player names for top contributors
        player_map = {
            f"{result['qb']} (QB)": result["ratings"]["QB"],
            f"{result['rb']} (RB)": result["ratings"]["RB"],
            f"{result['wr1']} (WR1)": result["ratings"]["WR1"],
            f"{result['wr2']} (WR2)": result["ratings"]["WR2"],
            f"{result['te']} (TE)": result["ratings"]["TE"],
            "Offensive Line (OL)": result["ratings"]["OL"]
        }

        top_players = sorted(player_map.items(), key=lambda x: x[1], reverse=True)[:3]

        print("\n🏆 Top 3 Offensive Contributors (by player):")
        for name, score in top_players:
            print(f"{name}: {score}")

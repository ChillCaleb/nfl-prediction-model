import sqlite3
import pandas as pd
import os

def rate_qb(passing_row, adv_passing_row, adv_rushing_row=None, verbose=False):
    """
    Calculates a quarterback's overall rating using passing and optional rushing stats.
    Normalized on a 0–100 scale. Prints whether each key attribute is found.
    """
    try:
        def get_val(row, col):
            if col in row:
                if verbose:
                    print(f"✅ Found '{col}'")
                return float(row[col])
            else:
                if verbose:
                    print(f"❌ Missing '{col}'")
                return 0.0

        # --- Passing Stats ---
        att = get_val(passing_row, "Att")
        cmp_pct = get_val(passing_row, "Cmp%")
        td_pct = get_val(passing_row, "TD") / att * 100 if att else 0.0
        int_pct = get_val(passing_row, "Int") / att * 100 if att else 0.0
        qbr = get_val(passing_row, "QBR")
        ay_a = get_val(passing_row, "AY/A")

        iay_pa = get_val(adv_passing_row, "IAY/PA")
        bad_pct = get_val(adv_passing_row, "Bad%")
        prss_pct = get_val(adv_passing_row, "Prss%")

        pass_rating = (
            0.15 * ((cmp_pct - 55) / 20) +
            0.20 * ((td_pct - 2) / 8) -
            0.15 * (int_pct / 5) +
            0.15 * (qbr / 100) +
            0.15 * ((ay_a - 5) / 5) +
            0.10 * ((iay_pa - 5) / 7) -
            0.05 * (bad_pct / 20) -
            0.05 * (prss_pct / 30)
        ) * 100

        rush_rating = 0
        if adv_rushing_row is not None:
            if verbose:
                print("\n🔁 Calculating QB rushing contribution...")
            rush_yds = get_val(adv_rushing_row, "Yds")
            rush_1d = get_val(adv_rushing_row, "1D")
            brk_tkl = get_val(adv_rushing_row, "BrkTkl")

            max_rush_yds = 800
            max_rush_1d = 40
            max_brk_tkl = 25

            rush_rating = (
                0.5 * (rush_yds / max_rush_yds) +
                0.3 * (rush_1d / max_rush_1d) +
                0.2 * (brk_tkl / max_brk_tkl)
            ) * 100

        if rush_rating < 25:
            if verbose:
                print(f"ℹ️ Rushing rating too low ({rush_rating:.2f}) — ignoring rushing impact.")
            final_rating = round(pass_rating, 2)
        else:
            final_rating = round(0.75 * pass_rating + 0.25 * rush_rating, 2)

        if verbose:
            print(f"📊 Passing Rating: {round(pass_rating, 2)}")
            print(f"🏃 Rushing Rating: {round(rush_rating, 2)}")

        return final_rating

    except Exception as e:
        if verbose:
            print(f"[QB RATING ERROR] {e}")
        return 0.0

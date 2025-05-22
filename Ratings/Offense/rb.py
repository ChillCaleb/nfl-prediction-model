import sqlite3
import pandas as pd
import os

def rate_rb(combo_row, adv_rush_row, adv_recv_row, verbose=False):
    """
    Calculate a running back rating using rushing and receiving contributions.
    Normalized on a 0–100 scale.
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

        rush_yds = get_val(adv_rush_row, "Yds")
        brk_tkl = get_val(adv_rush_row, "BrkTkl")
        rush_tds = get_val(combo_row, "('Rushing', 'TD')")
        ypc = get_val(combo_row, "('Rushing', 'Y/A')")
        rush_1d = get_val(combo_row, "('Rushing', '1D')")
        fumbles = get_val(combo_row, "('Unnamed: 31_level_0', 'Fmb')")

        rec_tgt = get_val(adv_recv_row, "Tgt")
        rec_rec = get_val(adv_recv_row, "Rec")
        rec_yds = get_val(adv_recv_row, "Yds")
        rec_tds = get_val(combo_row, "('Receiving', 'TD')")
        drop_pct = get_val(adv_recv_row, "Drop%")
        ypt = rec_yds / rec_tgt if rec_tgt else 0
        catch_pct = rec_rec / rec_tgt if rec_tgt else 0

        max_vals = {
            "rush_yds": 2200, "rush_tds": 18, "rush_1d": 90,
            "brk_tkl": 40, "ypc": 6.0, "fumbles": 6,
            "catch_pct": 1.0, "ypt": 12.0, "rec_yds": 1000,
            "rec_tds": 10, "drop_pct": 25
        }

        rush_rating = (
            0.30 * (rush_yds / max_vals["rush_yds"]) +
            0.20 * (ypc / max_vals["ypc"]) +
            0.15 * (rush_tds / max_vals["rush_tds"]) +
            0.15 * (rush_1d / max_vals["rush_1d"]) +
            0.15 * (brk_tkl / max_vals["brk_tkl"]) -
            0.10 * (fumbles / max_vals["fumbles"])
        ) * 100

        recv_rating = (
            0.25 * catch_pct +
            0.20 * (ypt / max_vals["ypt"]) +
            0.20 * (rec_yds / max_vals["rec_yds"]) +
            0.15 * (rec_tds / max_vals["rec_tds"]) -
            0.10 * (drop_pct / max_vals["drop_pct"])
        ) * 100

        final = round(0.6 * rush_rating + 0.4 * recv_rating, 2)

        if verbose:
            print(f"\n📊 Rushing Rating: {round(rush_rating, 2)}")
            print(f"📡 Receiving Rating: {round(recv_rating, 2)}")
            print(f"✅ Final RB Rating: {final}")

        return final

    except Exception as e:
        if verbose:
            print(f"[RB RATING ERROR] {e}")
        return 0.0

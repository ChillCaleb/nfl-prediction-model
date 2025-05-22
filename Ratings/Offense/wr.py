import sqlite3
import pandas as pd
import os

def rate_wr(row, verbose=False):
    """
    Rates a wide receiver using catch %, YPT, YAC, ADOT, TDs, drop rate, etc.
    Normalized on a 0–100 scale.
    """
    try:
        def get_val(col):
            if col in row:
                if verbose:
                    print(f"✅ Found '{col}'")
                return float(row[col])
            else:
                if verbose:
                    print(f"❌ Missing '{col}'")
                return 0.0

        tgt = get_val("Tgt")
        rec = get_val("Rec")
        yds = get_val("Yds")
        tds = get_val("1D")  # proxy for TDs
        yac = get_val("YAC/R")
        adot = get_val("ADOT")
        drop_pct = get_val("Drop%")

        catch_pct = rec / tgt if tgt else 0
        ypt = yds / tgt if tgt else 0

        rating = (
            0.2 * catch_pct +
            0.2 * (ypt / 12.0) +
            0.2 * (yds / 1800.0) +
            0.15 * (tds / 12.0) +
            0.1 * (yac / 10.0) +
            0.1 * (adot / 20.0) -
            0.05 * (drop_pct / 25.0)
        ) * 100

        return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[WR RATING ERROR] {e}")
        return 0.0

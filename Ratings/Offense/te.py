import sqlite3
import pandas as pd
import os

def rate_te(row, verbose=False):
    """
    Rates a tight end using catch %, YPT, TDs (1D proxy), YAC, drop rate.
    More red zone focused and volume tolerant than WRs.
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
        drop_pct = get_val("Drop%")

        catch_pct = rec / tgt if tgt else 0
        ypt = yds / tgt if tgt else 0

        rating = (
            0.25 * catch_pct +
            0.25 * (tds / 10.0) +
            0.2 * (ypt / 12.0) +
            0.15 * (yac / 10.0) +
            0.1 * (yds / 1000.0) -
            0.05 * (drop_pct / 25.0)
        ) * 100

        return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[TE RATING ERROR] {e}")
        return 0.0

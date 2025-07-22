import sqlite3
import pandas as pd
import os

def rate_wr(row, return_archetype=False, verbose=False):
    """
    Granular rating system for WRs based on yards, TDs, 1Ds, receptions, and errors.
    Archetypes apply bonus/penalty modifiers only.
    """
    try:
        def get_val(col):
            if col in row:
                val = row[col]
                if verbose:
                    print(f"✅ Found '{col}' = {val}")
                return float(val)
            else:
                if verbose:
                    print(f"❌ Missing '{col}'")
                return 0.0

        tgt = get_val("Tgt")
        rec = get_val("Rec")
        yds = get_val("Yds")
        one_d = get_val("1D")
        yac = get_val("YAC")
        adot = get_val("ADOT")
        drop_pct = get_val("Drop%")
        tds = get_val("TD") if "TD" in row else 0

        catch_pct = rec / tgt if tgt else 0
        ypt = yds / tgt if tgt else 0
        yac_r = yac / rec if rec else 0
        one_d_rate = one_d / rec if rec else 0

        # --- Archetype Classification ---
        archetype = "Balanced"
        special_title = ""
        if rec >= 70 and yds >= 1000 and catch_pct >= 0.65 and yac_r >= 3 and adot >= 8 and rec >= 40:
            archetype = "All-Around Elite"
        elif catch_pct >= 0.75 and adot <= 9 and ypt >= 7.5:
            archetype = "Volume Possession"
        elif yac_r >= 6.0 and adot <= 9:
            archetype = "YAC Specialist"
        elif adot >= 12 and ypt >= 9 and catch_pct <= 0.7:
            archetype = "Deep Threat"
        elif one_d_rate >= 0.7 and rec < 70:
            archetype = "Red Zone Scorer"
        elif one_d >= 50 and adot < 10 and drop_pct < 3.5:
            archetype = "Chain Mover"

        # --- Granular Additive Rating ---
        rating = 0
        rating += 0.01 * yds
        rating += 1.0 * tds
        rating += 0.5 * one_d
        rating += 0.25 * rec
        rating -= 0.5 * (drop_pct / 100.0) * tgt

        # --- Archetype Bonus / Penalty ---
        if archetype == "All-Around Elite":
            rating += 20
        elif archetype in ["Volume Possession", "YAC Specialist", "Deep Threat"]:
            rating += 5
        elif archetype in ["Red Zone Scorer", "Chain Mover"]:
            rating += 3
        else:
            rating -= 7

        if return_archetype:
            return round(rating, 2), archetype
        else:
            return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[WR RATING ERROR] {e}")
        return 0.0 if not return_archetype else (0.0, "Unknown")

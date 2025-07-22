import sqlite3
import pandas as pd
import os

def rate_te(row, return_archetype=False, verbose=False):
    """
    Granular rating system for TEs based on yards, 1Ds, receptions, and errors.
    Archetypes apply additive bonuses.
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
        tds = get_val("1D")
        yac = get_val("YAC/R")
        drop_pct = get_val("Drop%")

        catch_pct = rec / tgt if tgt else 0
        ypt = yds / tgt if tgt else 0

        archetype = "Balanced"
        special_title = ""

        # --- Archetype Classification ---
        if rec >= 60 and yds >= 800 and catch_pct >= 0.65 and yac >= 3 and tds >= 40:
            archetype = "All-Around Elite"
        elif catch_pct >= 0.75 and ypt >= 7:
            archetype = "Possession Mover"
        elif yac >= 6.0:
            archetype = "YAC Specialist"
        elif tds / rec >= 0.6:
            archetype = "Red Zone Threat"

        # --- Granular Additive Rating ---
        rating = 0
        rating += 0.01 * yds
        rating += 1.0 * tds
        rating += 0.25 * rec
        rating -= 0.5 * (drop_pct / 100.0) * tgt

        # --- Archetype Bonus ---
        if archetype == "All-Around Elite":
            rating += 12
        elif archetype in ["Possession Mover", "YAC Specialist"]:
            rating += 5
        elif archetype == "Red Zone Threat":
            rating += 3
        else:
            rating -= 7

        if return_archetype:
            return round(rating, 2), archetype
        else:
            return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[TE RATING ERROR] {e}")
        return 0.0 if not return_archetype else (0.0, "Unknown")
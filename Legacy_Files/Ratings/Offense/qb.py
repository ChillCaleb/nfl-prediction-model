import sqlite3
import pandas as pd
import os

def rate_qb(passing_row, adv_passing_row, adv_rushing_row=None, verbose=False):
    try:
        def get_val(row, col):
            return float(row[col]) if col in row and pd.notnull(row[col]) else 0.0

        att = get_val(passing_row, "Att")
        cmp = get_val(passing_row, "Cmp")
        yds = get_val(passing_row, "Yds")
        tds = get_val(passing_row, "TD")
        ints = get_val(passing_row, "Int")
        one_d = get_val(passing_row, "1D")

        # Archetype logic
        archetype = "Balanced"
        special = ""
        if cmp / att >= 0.70 and yds >= 4000 and tds >= 30 and ints <= 7:
            archetype = "All-Around Elite"
        elif tds / ints >= 4:
            archetype = "Efficient Scorer"
        elif yds >= 3500 and cmp / att >= 0.68:
            archetype = "Accurate Volume"

        # Check for dual threat using updated elite thresholds
        rush_yds = get_val(adv_rushing_row, "Yds") if adv_rushing_row is not None else 0
        brk_tkl = get_val(adv_rushing_row, "BrkTkl") if adv_rushing_row is not None else 0
        if (cmp / att >= 0.60 and yds >= 3000 and tds >= 20 and ints <= 9 and rush_yds >= 900 and brk_tkl >= 5):
            special = "Elite Dual Threat"

        elif rush_yds >= 500:
            archetype = "Dual Threat"

        # Final trimmed granular weights
        rating = 0
        rating += 0.003 * yds
        rating += 0.8 * tds
        rating += 0.15 * one_d
        rating += 0.1 * cmp

        if special == "Elite Dual Threat":
            rating -= 2.0 * ints  # reduced penalty for elite dual threat
        else:
            rating -= 6.0 * ints  # default INT penalty

        # Bonuses capped
        if archetype == "All-Around Elite":
            rating += 6
        elif archetype in ["Efficient Scorer", "Accurate Volume"]:
            rating += 4
        elif archetype == "Dual Threat":
            rating += 4 + 0.5 * rush_yds / 100
        else:
            rating -= 5

        if special == "Elite Dual Threat":
            rating += 5
            if verbose:
                print(f"📊 QB Rating: {round(rating, 2)} [Elite Dual Threat]")

        return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[QB RATING ERROR] {e}")
        return 0.0
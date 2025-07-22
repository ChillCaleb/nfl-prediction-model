import sqlite3
import pandas as pd
import os

def rate_rb(combo_row, adv_rush_row, adv_recv_row, return_archetype=False, verbose=False):
    """
    Granular RB rating with all-purpose additive logic.
    Archetypes provide bonus, no caps.
    """
    try:
        def get_val(row, col):
            return float(row[col]) if col in row and pd.notnull(row[col]) else 0.0

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
        rec_1d = get_val(combo_row, "('Receiving', '1D')")
        drop_pct = get_val(adv_recv_row, "Drop%")
        ypt = rec_yds / rec_tgt if rec_tgt else 0
        catch_pct = rec_rec / rec_tgt if rec_tgt else 0

        all_yds = rush_yds + rec_yds
        all_tds = rush_tds + rec_tds
        all_1d = rush_1d + rec_1d

        # --- Archetype Logic ---
        archetype = "Balanced"
        special_title = ""
        if rush_yds >= 1200 and ypc >= 4.5 and rush_1d >= 60 and brk_tkl >= 20:
            archetype = "All-Around Elite"
        elif rec_rec >= 25 and rec_yds >= 250 and ypt >= 6.0:
            archetype = "Receiving Back"
        elif rush_yds >= 1000 and ypc >= 4.2:
            archetype = "Ground and Pound"
        elif brk_tkl >= 30:
            archetype = "Tackle Breaker"

        # --- Granular Rating ---
        yard_val = 0.01 * all_yds
        td_val = 1.0 * all_tds
        fd_val = 0.5 * all_1d
        rec_val = 0.25 * rec_rec
        fmb_pen = 0.5 * fumbles
        drop_pen = 0.5 * (drop_pct / 100.0) * rec_tgt

        # --- Apply doubling if elite
        if archetype == "All-Around Elite":
            yard_val *= 2
            td_val *= 2
            fd_val *= 2
            rec_val *= 2

        rating = yard_val + td_val + fd_val + rec_val - fmb_pen - drop_pen

        # --- Archetype Bonuses ---
        if archetype == "All-Around Elite":
            rating += 7
        elif archetype == "Receiving Back":
            rating += 5 + .8 * rec_rec
        elif archetype == "Ground and Pound":
            rating += 5 + 1.5 * rush_yds / 100
        elif archetype == "Tackle Breaker":
            rating += 5 + 2.0 * brk_tkl
        else:
            rating -= 7

        if return_archetype:
            return round(rating, 2), archetype
        else:
            return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[RB RATING ERROR] {e}")
        return 0.0 if not return_archetype else (0.0, "Unknown")

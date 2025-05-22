import sqlite3
import pandas as pd
import os

def rate_ol(passing_df, adv_rush_df, combo_df, verbose=False):
    """
    Rates offensive line as a unit using:
    - Sack % from passing
    - Yards before contact (YBC/Att) from advanced_rushing
    - Rushing 1Ds from rushing_and_receiving
    Returns rating on 0–100 scale.
    """
    try:
        def safe_avg(series):
            try:
                return pd.to_numeric(series, errors='coerce').mean()
            except:
                return 0.0

        sack_rate = pd.to_numeric(passing_df["Sk%"], errors='coerce').mean() / 100.0
        ybc_att = safe_avg(adv_rush_df["YBC/Att"])
        rush_1d = pd.to_numeric(combo_df["('Rushing', '1D')"], errors='coerce').sum()

        rating = (
            0.3 * (1 - sack_rate) +
            0.4 * (ybc_att / 3.5) +
            0.3 * (rush_1d / 150.0)
        ) * 100

        return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[OL RATING ERROR] {e}")
        return 0.0

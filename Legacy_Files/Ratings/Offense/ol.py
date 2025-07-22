import sqlite3
import pandas as pd
import os

def rate_ol(passing_df, adv_rush_df, combo_df, verbose=False):
    """
    Rates offensive line as a unit using:
    - Sack % from passing
    - Yards before contact (YBC/Att) from advanced_rushing
    - Rushing 1Ds from rushing_and_receiving
    Applies penalties and scaling to prevent inflation while allowing exceptional units to exceed 100.
    """
    try:
        def safe_avg(series):
            try:
                return pd.to_numeric(series, errors='coerce').mean()
            except:
                return 0.0

        sack_rate = pd.to_numeric(passing_df["Sk%"], errors='coerce').mean() / 100.0
        ybc_att = safe_avg(adv_rush_df["YBC/Att"])
        rush_1d = pd.to_numeric(combo_df["Rushing - 1D"], errors='coerce').sum()

        # Core scoring factors
        protection_score = (1 - sack_rate) * 100          # Higher is better
        push_score = (ybc_att / 3.5) * 100                 # Relative to benchmark
        conversion_score = (rush_1d / 150.0) * 100         # Relative to strong total

        # Penalize sack_rate > 9% heavily
        sack_penalty = 0
        if sack_rate > 0.09:
            sack_penalty = (sack_rate - 0.09) * 400        # scale up past tolerance

        # Slight bonus for high YBC efficiency
        ybc_bonus = 0
        if ybc_att >= 4.0:
            ybc_bonus = (ybc_att - 4.0) * 10

        rating = (
            0.4 * protection_score +
            0.3 * push_score +
            0.3 * conversion_score +
            ybc_bonus - sack_penalty
        )

        if verbose:
            print(f"📊 OL Rating → Protection: {protection_score:.2f}, Push: {push_score:.2f}, 1Ds: {conversion_score:.2f}, Penalty: {sack_penalty:.2f}, Bonus: {ybc_bonus:.2f}, Final: {rating:.2f}")

        return round(rating, 2)

    except Exception as e:
        if verbose:
            print(f"[OL RATING ERROR] {e}")
        return 0.0
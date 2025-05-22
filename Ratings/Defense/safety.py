import sqlite3
import pandas as pd

def flatten_columns(df):
    df.columns = [f"{c[0]}_{c[1]}".strip(" _") if isinstance(c, tuple) else c for c in df.columns]
    return df

def rate_safety(team: str, db_path: str, verbose=False) -> float:
    table_name = f"team_{team.lower()}_defense"
    adv_table = f"team_{team.lower()}_advanced_defense"

    conn = sqlite3.connect(db_path)

    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        adv_df = pd.read_sql_query(f"SELECT * FROM {adv_table}", conn)
        conn.close()

        if df.empty and adv_df.empty:
            return 0.0

        df = flatten_columns(df)
        df = df.fillna(0)
        adv_df = adv_df.fillna(0)

        def get_val(df, col):
            return pd.to_numeric(df[col], errors='coerce').mean() if col in df else 0.0

        # Core safety metrics: coverage + support
        pd = get_val(df, "Def Interceptions_PD")
        interceptions = get_val(df, "Def Interceptions_Int")
        tackles = get_val(df, "Tackles_Comb")
        missed_pct = get_val(adv_df, "MTkl%")
        cmp_pct = get_val(adv_df, "Cmp%")
        yds_per_cmp = get_val(adv_df, "Yds/Cmp")
        rating_allowed = get_val(adv_df, "Rat")
        deep_tackles = get_val(df, "Tackles_Solo")

        rating = (
            0.20 * (interceptions / 5.0) +
            0.15 * (pd / 10.0) +
            0.15 * (tackles / 110.0) +
            0.10 * (deep_tackles / 70.0) -
            0.10 * (missed_pct / 25.0) -
            0.10 * (cmp_pct / 80.0) -
            0.10 * (yds_per_cmp / 15.0) -
            0.10 * (rating_allowed / 120.0)
        ) * 100

        rating = round(rating, 2)

        if verbose:
            print(f"Safety Rating: {rating}")

        return rating

    except Exception as e:
        if verbose:
            print(f"[SAFETY RATING ERROR] {e}")
        return 0.0

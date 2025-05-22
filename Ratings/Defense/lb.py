import sqlite3
import pandas as pd

def flatten_columns(df):
    df.columns = [f"{c[0]}_{c[1]}".strip(" _") if isinstance(c, tuple) else c for c in df.columns]
    return df

def rate_lb(team: str, db_path: str, verbose=False) -> float:
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

        # Pull values from both tables
        comb = get_val(df, "Tackles_Comb")
        solo = get_val(df, "Tackles_Solo")
        tfl = get_val(df, "Tackles_TFL")
        qbhits = get_val(df, "Tackles_QBHits")

        blitz = get_val(adv_df, "Bltz")
        hrry = get_val(adv_df, "Hrry")
        qbkd = get_val(adv_df, "QBKD")
        missed_pct = get_val(adv_df, "MTkl%")
        interceptions = get_val(adv_df, "Int")
        passes_defended = get_val(adv_df, "Cmp%")  # inverse of completion % as proxy

        rating = (
            0.2 * (comb / 120.0) +
            0.1 * (solo / 80.0) +
            0.15 * (tfl / 12.0) +
            0.10 * (qbhits / 15.0) +
            0.10 * (blitz / 25.0) +
            0.10 * (hrry / 20.0) +
            0.10 * (qbkd / 10.0) +
            0.05 * (interceptions / 5.0) -
            0.10 * (missed_pct / 25.0)
        ) * 100

        rating = round(rating, 2)

        if verbose:
            print(f"LB Rating: {rating}")

        return rating

    except Exception as e:
        if verbose:
            print(f"[LB RATING ERROR] {e}")
        return 0.0

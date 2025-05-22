import sqlite3
import pandas as pd

def flatten_columns(df):
    df.columns = [f"{c[0]}_{c[1]}".strip(" _") if isinstance(c, tuple) else c for c in df.columns]
    return df

def rate_dl(team: str, db_path: str, verbose=False) -> float:
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
        adv_df = adv_df.fillna(0)
        df = df.fillna(0)

        def get_val(df, col):
            return pd.to_numeric(df[col], errors='coerce').mean() if col in df else 0.0

        # Key metrics (defense.csv + advanced_defense.csv)
        tfl = get_val(df, "Tackles_TFL")
        qbhits = get_val(df, "Tackles_QBHits")
        sacks = get_val(df, "Unnamed: 16_level_0_Sk")
        pressures = get_val(adv_df, "Prss")
        hurries = get_val(adv_df, "Hrry")
        qbkd = get_val(adv_df, "QBKD")
        batted = get_val(adv_df, "Bats")
        miss_tkl_pct = get_val(adv_df, "MTkl%")

        # Rating formula with balanced weights
        rating = (
            0.2 * (sacks / 15.0) +
            0.15 * (pressures / 30.0) +
            0.15 * (tfl / 12.0) +
            0.10 * (qbhits / 20.0) +
            0.10 * (hurries / 20.0) +
            0.10 * (qbkd / 10.0) +
            0.10 * (batted / 8.0) -
            0.10 * (miss_tkl_pct / 25.0)
        ) * 100

        rating = round(rating, 2)

        if verbose:
            print(f"DL Rating: {rating}")

        return rating

    except Exception as e:
        if verbose:
            print(f"[DL RATING ERROR] {e}")
        return 0.0

import pandas as pd
from pathlib import Path

RAW_ROOT = Path("NFL")
DEFENSE_PATTERN = "**/defense.csv"

def clean_defense_csv(file_path):
    try:
        df_raw = pd.read_csv(file_path, header=None)

        # Drop any rows that contain label-like strings (not actual player data)
        bad_rows = df_raw.apply(
            lambda row: row.astype(str).str.contains("Tackles|Fumbles|Def|Interceptions|Unnamed", case=False).any(),
            axis=1
        )
        df_clean = df_raw[~bad_rows].reset_index(drop=True)

        # Manually define correct headers
        headers = [
            "Rk", "Player", "Age", "Pos", "G", "GS",
            "Int", "Yds", "IntTD", "Lng",
            "PD", "FF", "Fmb", "FR", "Yds_Fum", "FRTD",
            "Sk", "Comb", "Solo", "Ast", "TFL", "QBHits",
            "Sfty", "Awards"
        ]

        df_clean.columns = headers
        df_clean.to_csv(file_path, index=False)
        print(f"[✓] Manually cleaned and labeled defense.csv: {file_path}")
    except Exception as e:
        print(f"[!] Failed to clean {file_path}: {e}")

def run_cleaning():
    base = Path(".").resolve()
    raw_root = base / RAW_ROOT

    for file in raw_root.glob(DEFENSE_PATTERN):
        if "advanced" not in str(file):
            clean_defense_csv(file)

if __name__ == "__main__":
    run_cleaning()

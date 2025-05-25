import pandas as pd
from pathlib import Path

# Locate all rushing_and_receiving.csv files
rr_paths = list(Path("NFL").rglob("rushing_and_receiving.csv"))

for path in rr_paths:
    try:
        # Load raw file with no headers
        df_raw = pd.read_csv(path, header=None)

        # Use row 1 (index 1) as the actual header row
        headers = df_raw.iloc[1].tolist()

        # Drop only the row used as header (index 1), keep Jerry Jeudy and everyone else
        df_clean = df_raw.drop(index=1).reset_index(drop=True)
        df_clean.columns = headers

        # Overwrite the file with the cleaned version
        df_clean.to_csv(path, index=False)
        print(f"[✓] Cleaned: {path}")
    except Exception as e:
        print(f"[!] Failed to clean {path}: {e}")

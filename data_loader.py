import pandas as pd
import os
from constants import full_to_abbr

# Base path where the project folders (AFC/NFC) live
BASE_PATH = os.path.dirname(__file__)

# Internal storage: abbreviation → DataFrame
_dfs = {}

# -------------------------------
# Normalize filename to team abbr
# -------------------------------
# -------------------------------
# Load all CSVs from AFC/NFC tree
# -------------------------------
def load_all_team_csvs():
    print("📦 Starting team data load...")

    for conference in ["AFC", "NFC"]:
        conf_path = os.path.join(BASE_PATH, conference)
        if not os.path.exists(conf_path):
            print(f"⚠️ Missing path: {conf_path}")
            continue

        for division in os.listdir(conf_path):
            div_path = os.path.join(conf_path, division)
            if not os.path.isdir(div_path):
                continue

            for team in os.listdir(div_path):
                team_path = os.path.join(div_path, team)
                if not os.path.isdir(team_path):
                    continue

                for file in os.listdir(team_path):
                    if file.startswith("._"):
                        continue  # Skip macOS junk
                    if file.endswith(".csv") and "_BS" in file:
                        full_path = os.path.join(team_path, file)

# -------------------------------
# Get/set/update DataFrame access
# -------------------------------
def get_df(abbr):
    if abbr not in _dfs:
        raise ValueError(f"Team '{abbr}' not loaded yet.")
    return _dfs[abbr]

def set_df(abbr, df):
    _dfs[abbr] = df
    print(f"📌 Set new DataFrame for {abbr} with {len(df)} rows")

def update_df(abbr, **cols):
    df = get_df(abbr) if abbr in _dfs else pd.DataFrame()
    if df.empty:
        df = pd.DataFrame({name: [val] for name, val in cols.items()})
    else:
        for name, val in cols.items():
            df[name] = val
    set_df(abbr, df)

#--------------------------
# Load league-wide full schedule
# -------------------------------
_schedule_df = None

def get_schedule_df():
    global _schedule_df
    if _schedule_df is None:
        path = os.path.join(BASE_PATH, "NFL", "Full_Schedule.csv")
    return _schedule_df

# ============================
# 🏈 League-Wide Team-Level Stats Loaders
# ============================

BASE_PATH = os.path.dirname(__file__)

# Build abbreviation to full name mapping
abbr_to_full = {abbr: full for full, abbr in full_to_abbr.items()}

# --- Raw Data Loaders ---
def get_team_row_from_schedule(df, team_input):
    """
    Retrieves the row for a team from an official NFL schedule DataFrame.
    This assumes the DataFrame uses 'Winner/tie' and 'Loser/tie' columns.
    """
    print(f"🔎 Looking for team: '{team_input}' in schedule...")

    if not isinstance(team_input, str) or team_input.strip().lower() == "nan":
        raise ValueError("❌ Invalid team_input: input is missing or malformed.")

    team_name = team_input.strip().upper()

    # Normalize both columns
    df_normalized = df.copy()
    df_normalized["Winner/tie"] = df["Winner/tie"].astype(str).str.strip().str.upper()
    df_normalized["Loser/tie"]  = df["Loser/tie"].astype(str).str.strip().str.upper()

    match = df_normalized[
        (df_normalized["Winner/tie"] == team_name) |
        (df_normalized["Loser/tie"] == team_name)
    ]

    if match.empty:
        raise ValueError(f"❌ Team '{team_input}' not found in schedule.")

    print(f"✅ Match found for team: '{team_input}'")
    return match

def get_team_row(df, team_input, column=None):
    """
    Retrieves the row for a team from any general team-based DataFrame.
    Defaults to looking in 'Tm' column unless specified.
    """
    from constants import abbr_to_full

    if team_input in abbr_to_full:
        team_name = abbr_to_full[team_input]
    else:
        team_name = team_input

    if column is None:
        for possible in ["Tm", "Team"]:
            if possible in df.columns:
                column = possible
                break

    if column is None:
        raise ValueError("❌ No valid team-identifying column found in dataframe.")

    row = df[df[column].astype(str).str.strip().str.upper() == str(team_name).strip().upper()]
    if row.empty:
        raise ValueError(f"❌ Team '{team_input}' not found in column '{column}'")

    return row.iloc[0]


# ============================
#  Offense
# ============================

def get_team_total_offense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_team_total_offense.csv")
    return pd.read_csv(file_path)


def get_team_situational_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_team_situational.csv")
    return pd.read_csv(file_path)

def get_team_drive_stats_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_team_drive_stats.csv")
    return pd.read_csv(file_path)

def get_rushing_offense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_rushing_offense.csv")
    return pd.read_csv(file_path)

def get_passing_offense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_passing_offense.csv")
    return pd.read_csv(file_path)

def get_total_offense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_team_total_offense.csv")
    return pd.read_csv(file_path)

# ============================
# Defense
# ============================

def get_total_defense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "Total_Defense.csv")
    return pd.read_csv(file_path)

def get_situational_defense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_situational_defense.csv")
    return pd.read_csv(file_path)

def get_drive_defense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_drive_defense.csv")
    return pd.read_csv(file_path)

def get_rushing_defense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_rushing_defense.csv")
    return pd.read_csv(file_path)

def get_passing_defense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_passing_defense.csv")
    return pd.read_csv(file_path)

def get_total_offense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_team_total_offense.csv")
    return pd.read_csv(file_path)


def get_scoring_defense_df():
    file_path = os.path.join(BASE_PATH, "NFL", "cleaned_scoring_defense.csv")
    return pd.read_csv(file_path)


# ============================
#  Special Teams
# ============================

def get_special_teams_df():
    file_path = os.path.join(BASE_PATH, "NFL", "Total_Special_Teams.csv")
    return pd.read_csv(file_path)


# ============================
#  League-Wide 
# ============================


def get_schedule_df():
    file_path = os.path.join(BASE_PATH, "NFL", "Full_Schedule.csv")
    return pd.read_csv(file_path)

def get_team_boxscore_df(team_abbr):
    file_name = f"24_{team_abbr.lower()}_BS.csv"
    folder_path = os.path.join(BASE_PATH, team_abbr)
    full_path = os.path.join(folder_path, file_name)
    return pd.read_csv(full_path)

# --- Team Rating Cache Interface ---

_dfs = {}

def get_df(abbr):
    return _dfs.get(abbr, pd.DataFrame())

def set_df(abbr, df):
    _dfs[abbr] = df

def update_df(abbr, **cols):
    df = get_df(abbr).copy()
    for col, val in cols.items():
        df[col] = [val]
    set_df(abbr, df)
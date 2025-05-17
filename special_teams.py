# special_teams.py

from data_loader import get_team_row, get_special_teams_df, update_df
from sklearn.preprocessing import MinMaxScaler

def safe_float(value):
    if isinstance(value, str):
        value = value.strip().replace('%', '')
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def calc_special_teams_rating(team_abbr):
    df = get_special_teams_df()
    row = get_team_row(df, team_abbr)

    # Using correct keys based on your CSV structure
    keys = ["FG%", "XP%", "TB%", "KOAvg"]
    weights = {"FG%": 0.30, "XP%": 0.25, "TB%": 0.20, "KOAvg": 0.25}

    scores = {}
    for key in keys:
        league = df[key].map(safe_float).values.reshape(-1, 1)
        scaler = MinMaxScaler().fit(league)
        val = safe_float(row[key])
        scores[key] = scaler.transform([[val]])[0][0]

    score = sum(scores[k] * weights[k] for k in keys) * 100
    update_df(team_abbr, special_rating=score)
    return score

# defense.py
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from Engine.strength_of_schedule import apply_sos_modifier
from Engine.constants import column_mappings
from Engine.data_loader import (
    get_rushing_defense_df,
    get_passing_defense_df,
    get_total_defense_df,
    get_situational_defense_df,
    get_drive_defense_df,
    get_team_row,
    update_df,
)
def resolve_column(df, key):
    for variant in column_mappings.get(key, []):
        if variant in df.columns:
            return variant
    raise KeyError(f"❌ No matching column for: {key}")

def safe_float(value):
    if isinstance(value, str):
        value = value.strip().replace('%', '')
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def calc_rushing_defense(team_abbr, sos_dict, league_avg):
    df = get_rushing_defense_df()
    row = get_team_row(df, team_abbr)

    keys = ["Yds", "TD", "Y/A", "Y/G", "EXP"]
    scalers = {}
    values = {}

    for key in keys:
        col = resolve_column(df, key) if key in column_mappings else key
        league = df[col].map(safe_float).values.reshape(-1, 1)
        scaler = MinMaxScaler().fit(league)
        val = safe_float(row[col])
        values[key] = 1 - scaler.transform([[val]])[0][0]

    base_score = (
        values["Yds"] * 0.25 +
        values["TD"]  * 0.20 +
        values["Y/A"] * 0.20 +
        values["Y/G"] * 0.20 +
        values["EXP"] * 0.15
    ) * 100

    final_score = apply_sos_modifier(base_score, team_abbr, sos_dict, league_avg)
    update_df(team_abbr, rushing_defense_rating=final_score)
    return final_score

def calc_passing_defense(team_abbr, sos_dict, league_avg):
    df = get_passing_defense_df()
    row = get_team_row(df, team_abbr)

    keys = ["Cmp%", "Yds", "TD", "NY/A", "ANY/A", "Sk", "EXP"]
    scalers = {}
    values = {}

    for key in keys:
        col = resolve_column(df, key) if key in column_mappings else key
        league = df[col].map(safe_float).values.reshape(-1, 1)
        scaler = MinMaxScaler().fit(league)
        val = safe_float(row[col])
        values[key] = scaler.transform([[val]])[0][0] if key == "Sk" else 1 - scaler.transform([[val]])[0][0]

    base_score = (
        values["Cmp%"]  * 0.15 +
        values["Yds"]   * 0.15 +
        values["TD"]    * 0.15 +
        values["NY/A"]  * 0.15 +
        values["ANY/A"] * 0.15 +
        values["Sk"]    * 0.15 +
        values["EXP"]   * 0.10
    ) * 100

    final_score = apply_sos_modifier(base_score, team_abbr, sos_dict, league_avg)
    update_df(team_abbr, passing_defense_rating=final_score)
    return final_score

def calc_scoring_defense(team_abbr, sos_dict, league_avg):
    df_total = get_total_defense_df()
    df_situ  = get_situational_defense_df()
    df_drive = get_drive_defense_df()

    row_total = get_team_row(df_total, team_abbr)
    row_situ  = get_team_row(df_situ, team_abbr)
    row_drive = get_team_row(df_drive, team_abbr)

    col_pts_allowed = resolve_column(df_total, "Points_For")
    col_ypp_allowed = resolve_column(df_total, "Yards_Per_Play")
    col_third_down  = resolve_column(df_situ, "Third_Down_Efficiency")
    col_red_zone    = resolve_column(df_situ, "Red_Zone_Efficiency")
    col_takeaways   = resolve_column(df_drive, "Turnovers")

    league_pts_allowed = df_total[col_pts_allowed].map(safe_float).values.reshape(-1, 1)
    league_ypp_allowed = df_total[col_ypp_allowed].map(safe_float).values.reshape(-1, 1)
    league_third_down  = df_situ[col_third_down].map(safe_float).values.reshape(-1, 1)
    league_red_zone    = df_situ[col_red_zone].map(safe_float).values.reshape(-1, 1)
    league_takeaways   = df_drive[col_takeaways].map(safe_float).values.reshape(-1, 1)

    scaler_pts = MinMaxScaler().fit(league_pts_allowed)
    scaler_ypp = MinMaxScaler().fit(league_ypp_allowed)
    scaler_3d  = MinMaxScaler().fit(league_third_down)
    scaler_rz  = MinMaxScaler().fit(league_red_zone)
    scaler_to  = MinMaxScaler().fit(league_takeaways)

    pts_allowed = scaler_pts.transform([[safe_float(row_total[col_pts_allowed])]])[0][0]
    ypp_allowed = scaler_ypp.transform([[safe_float(row_total[col_ypp_allowed])]])[0][0]
    third_down  = scaler_3d.transform([[safe_float(row_situ[col_third_down])]])[0][0]
    red_zone    = scaler_rz.transform([[safe_float(row_situ[col_red_zone])]])[0][0]
    takeaways   = scaler_to.transform([[safe_float(row_drive[col_takeaways])]])[0][0]

    base_score = (
        (1 - pts_allowed) * 0.3 +
        (1 - ypp_allowed) * 0.2 +
        (1 - third_down)  * 0.15 +
        (1 - red_zone)    * 0.15 +
        takeaways         * 0.2
    ) * 100

    final_score = apply_sos_modifier(base_score, team_abbr, sos_dict, league_avg)
    update_df(team_abbr, scoring_defense_rating=final_score)
    return final_score

def calc_total_defense(team_abbr, sos_dict, league_avg):
    rushing = calc_rushing_defense(team_abbr, sos_dict, league_avg)
    passing = calc_passing_defense(team_abbr, sos_dict, league_avg)
    scoring = calc_scoring_defense(team_abbr, sos_dict, league_avg)

    score = rushing * 0.3 + passing * 0.3 + scoring * 0.4
    update_df(team_abbr, total_defense_rating=score)
    return score

from Engine.player_ratings import get_team_positional_ratings

def calculate_defensive_ratings(team_name: str, year: int) -> dict:
    ratings = get_team_positional_ratings(team_name, year)

    # Example: Use LB and DB as stand-ins for defense types
    run_defense = ratings.get("LB", 0)  # Linebackers
    pass_defense = ratings.get("DB", 0)  # Defensive backs
    total_defense = run_defense + pass_defense

    return {
        "Run Defense": run_defense,
        "Pass Defense": pass_defense,
        "Total Defense": total_defense
    }

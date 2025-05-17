# offense.py

import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from strength_of_schedule import apply_sos_modifier
from constants import column_mappings
from data_loader import (
    get_rushing_offense_df,
    get_passing_offense_df,
    get_team_total_offense_df,
    get_team_situational_df,
    get_team_drive_stats_df,
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

def calc_rushing_offense(team_abbr, sos_dict, league_avg):
    df = get_rushing_offense_df()
    row = get_team_row(df, team_abbr)

    keys = ["Yds", "TD", "Y/A", "Y/G", "EXP"]
    scalers = {}
    values = {}

    for key in keys:
        col = resolve_column(df, key) if key in column_mappings else key
        league = df[col].map(safe_float).values.reshape(-1, 1)
        scalers[key] = MinMaxScaler().fit(league)
        value = safe_float(row[col])
        values[key] = scalers[key].transform([[value]])[0][0]

    base_score = (
        values["Yds"] * 0.25 +
        values["TD"]  * 0.20 +
        values["Y/A"] * 0.20 +
        values["Y/G"] * 0.20 +
        values["EXP"] * 0.15
    ) * 100

    final_score = apply_sos_modifier(base_score, team_abbr, sos_dict, league_avg)
    update_df(team_abbr, rushing_rating=final_score)
    return final_score

def calc_passing_offense(team_abbr, sos_dict, league_avg):
    df = get_passing_offense_df()
    row = get_team_row(df, team_abbr)

    keys = ["Cmp%", "Yds", "TD", "Y/A", "NY/A", "ANY/A", "EXP"]
    scalers = {}
    values = {}

    for key in keys:
        col = resolve_column(df, key) if key in column_mappings else key
        league = df[col].map(safe_float).values.reshape(-1, 1)
        scalers[key] = MinMaxScaler().fit(league)
        value = safe_float(row[col])
        values[key] = scalers[key].transform([[value]])[0][0]

    base_score = (
        values["Cmp%"]  * 0.20 +
        values["Yds"]   * 0.20 +
        values["TD"]    * 0.15 +
        values["Y/A"]   * 0.15 +
        values["NY/A"]  * 0.10 +
        values["ANY/A"] * 0.10 +
        values["EXP"]   * 0.10
    ) * 100

    final_score = apply_sos_modifier(base_score, team_abbr, sos_dict, league_avg)
    update_df(team_abbr, passing_rating=final_score)
    return final_score

def calc_scoring_offense(team_abbr, sos_dict, league_avg):
    df_total = get_team_total_offense_df()
    df_situ  = get_team_situational_df()
    df_drive = get_team_drive_stats_df()

    row_total = get_team_row(df_total, team_abbr)
    row_situ  = get_team_row(df_situ, team_abbr)
    row_drive = get_team_row(df_drive, team_abbr)

    col_ppg        = resolve_column(df_total, "Points_For")
    col_ypp        = resolve_column(df_total, "Yards_Per_Play")
    col_third_down = resolve_column(df_situ, "Third_Down_Efficiency")
    col_red_zone   = resolve_column(df_situ, "Red_Zone_Efficiency")
    col_turnovers  = resolve_column(df_drive, "Turnovers")

    league_ppg        = df_total[col_ppg].map(safe_float).values.reshape(-1, 1)
    league_ypp        = df_total[col_ypp].map(safe_float).values.reshape(-1, 1)
    league_third_down = df_situ[col_third_down].map(safe_float).values.reshape(-1, 1)
    league_red_zone   = df_situ[col_red_zone].map(safe_float).values.reshape(-1, 1)
    league_turnovers  = df_drive[col_turnovers].map(safe_float).values.reshape(-1, 1)

    scaler_ppg = MinMaxScaler().fit(league_ppg)
    scaler_ypp = MinMaxScaler().fit(league_ypp)
    scaler_3d  = MinMaxScaler().fit(league_third_down)
    scaler_rz  = MinMaxScaler().fit(league_red_zone)
    scaler_to  = MinMaxScaler().fit(league_turnovers)

    ppg        = scaler_ppg.transform([[safe_float(row_total[col_ppg])]])[0][0]
    ypp        = scaler_ypp.transform([[safe_float(row_total[col_ypp])]])[0][0]
    third_down = scaler_3d.transform([[safe_float(row_situ[col_third_down])]])[0][0]
    red_zone   = scaler_rz.transform([[safe_float(row_situ[col_red_zone])]])[0][0]
    turnovers  = scaler_to.transform([[safe_float(row_drive[col_turnovers])]])[0][0]

    base_score = (
        ppg * 0.3 +
        ypp * 0.2 +
        third_down * 0.15 +
        red_zone * 0.15 -
        turnovers * 0.1
    ) * 100

    final_score = apply_sos_modifier(base_score, team_abbr, sos_dict, league_avg)
    update_df(team_abbr, scoring_rating=final_score)
    return final_score

def calc_total_offense(team_abbr, sos_dict, league_avg):
    rushing = calc_rushing_offense(team_abbr, sos_dict, league_avg)
    passing = calc_passing_offense(team_abbr, sos_dict, league_avg)
    scoring = calc_scoring_offense(team_abbr, sos_dict, league_avg)

    score = rushing * 0.3 + passing * 0.3 + scoring * 0.4
    update_df(team_abbr, total_offense_rating=score)
    return score

import itertools
import re
import sqlite3
from functools import lru_cache

import pandas as pd
from player_injection import inject_all_teams
from Legacy_Files.Engine.constants import abbr_to_full, team_name_alias
from Legacy_Files.Engine.data_loader import get_schedule_df

DB_PATH = "Database/nfl_ratings.db"


TEAM_NAME_ALIASES = {
    full_name: team_name_alias[abbr]
    for abbr, full_name in abbr_to_full.items()
}

OFFENSIVE_POSITIONS = {
    "qb": ("QB",),
    "rb": ("RB",),
    "wr": ("WR",),
    "te": ("TE",),
    "ol": ("OL",),
}

DEFENSIVE_POSITIONS = {
    "cb": ("C", "CB", "DB", "LCB", "RCB"),
    "dl": ("D", "DL", "DE", "DT", "EDGE", "NT", "LE", "RE", "LDE", "RDE"),
    "lb": ("L", "LB", "MLB", "ILB", "OLB", "WLB", "SLB", "LOLB", "ROLB"),
    "s": ("S", "SS", "FS"),
}


def slugify(value):
    value = str(value).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def safe_float(value):
    return float(pd.to_numeric(value, errors="coerce")) if value is not None else 0.0


def first_or_zero(row, column):
    if row is None or row.empty or column not in row:
        return 0.0
    return safe_float(row.iloc[0][column])


def aggregate_players(players, raw_column="raw", normalized_column="normalized"):
    if players.empty:
        return {
            "count": 0.0,
            "top_raw": 0.0,
            "top_norm": 0.0,
            "top3_raw_mean": 0.0,
            "top5_raw_sum": 0.0,
            "starter_raw_count": 0.0,
            "impact_raw_count": 0.0,
        }

    raw = pd.to_numeric(players[raw_column], errors="coerce").fillna(0.0).sort_values(ascending=False)
    normalized = pd.to_numeric(players.get(normalized_column, 0.0), errors="coerce").fillna(0.0)

    return {
        "count": float(len(players)),
        "top_raw": float(raw.iloc[0]),
        "top_norm": float(normalized.max()),
        "top3_raw_mean": float(raw.head(3).mean()),
        "top5_raw_sum": float(raw.head(5).sum()),
        "starter_raw_count": float((raw >= 50).sum()),
        "impact_raw_count": float((raw >= 80).sum()),
    }


@lru_cache(maxsize=1)
def load_rating_data():
    conn = sqlite3.connect(DB_PATH)
    off_team = pd.read_sql_query("SELECT * FROM Offensive_team_ratings", conn)
    def_team = pd.read_sql_query("SELECT * FROM Defensive_team_ratings", conn)
    off_players = pd.read_sql_query("SELECT * FROM Offensive_player_ratings", conn)
    def_players = pd.read_sql_query("SELECT * FROM Defensive_player_ratings", conn)
    conn.close()

    off_team = off_team.groupby("team", as_index=True).mean(numeric_only=True)
    def_team = def_team.groupby("team", as_index=True).mean(numeric_only=True)

    off_players = off_players.drop_duplicates(subset=["team", "player", "pos", "archetype"])
    def_players = def_players.drop_duplicates(subset=["team", "player", "pos", "archetype"])

    off_players["arch_slug"] = off_players["archetype"].apply(slugify)
    def_players["arch_slug"] = def_players["archetype"].apply(slugify)

    return {
        "off_team": off_team,
        "def_team": def_team,
        "off_players": off_players,
        "def_players": def_players,
        "off_archetypes": tuple(sorted(off_players["arch_slug"].dropna().unique())),
        "def_archetypes": tuple(sorted(def_players["arch_slug"].dropna().unique())),
    }


def team_rating_profile(team, rating_data=None):
    rating_data = rating_data or load_rating_data()
    off_team = rating_data["off_team"]
    def_team = rating_data["def_team"]
    off_players = rating_data["off_players"]
    def_players = rating_data["def_players"]

    profile = {}
    off_row = off_team.loc[[team]] if team in off_team.index else pd.DataFrame()
    def_row = def_team.loc[[team]] if team in def_team.index else pd.DataFrame()

    for unit, row in [("off", off_row), ("def", def_row)]:
        for column in ["rushing", "passing", "scoring", "total"]:
            profile[f"{unit}_{column}_rating"] = first_or_zero(row, column)

    profile["team_total_rating"] = profile["off_total_rating"] + profile["def_total_rating"]
    profile["team_pass_net_rating"] = profile["off_passing_rating"] + profile["def_passing_rating"]
    profile["team_rush_net_rating"] = profile["off_rushing_rating"] + profile["def_rushing_rating"]
    profile["team_score_net_rating"] = profile["off_scoring_rating"] + profile["def_scoring_rating"]

    team_off_players = off_players[off_players["team"].str.lower() == team.lower()]
    team_def_players = def_players[def_players["team"].str.lower() == team.lower()]

    for group_name, positions in OFFENSIVE_POSITIONS.items():
        group_players = team_off_players[team_off_players["pos"].str.upper().isin(positions)]
        for metric, value in aggregate_players(group_players).items():
            profile[f"off_{group_name}_{metric}"] = value

    for group_name, positions in DEFENSIVE_POSITIONS.items():
        group_players = team_def_players[team_def_players["pos"].str.upper().isin(positions)]
        for metric, value in aggregate_players(group_players).items():
            profile[f"def_{group_name}_{metric}"] = value
        for column in ["rushing", "passing", "scoring"]:
            if group_players.empty or column not in group_players:
                profile[f"def_{group_name}_{column}_mean"] = 0.0
                profile[f"def_{group_name}_{column}_top"] = 0.0
            else:
                values = pd.to_numeric(group_players[column], errors="coerce").fillna(0.0)
                profile[f"def_{group_name}_{column}_mean"] = float(values.mean())
                profile[f"def_{group_name}_{column}_top"] = float(values.max())

    for side, players, archetypes in [
        ("off", team_off_players, rating_data["off_archetypes"]),
        ("def", team_def_players, rating_data["def_archetypes"]),
    ]:
        for archetype in archetypes:
            archetype_players = players[players["arch_slug"] == archetype]
            profile[f"{side}_has_arch_{archetype}"] = float(not archetype_players.empty)
            profile[f"{side}_arch_{archetype}_count"] = float(len(archetype_players))
            profile[f"{side}_arch_{archetype}_top_raw"] = (
                float(pd.to_numeric(archetype_players["raw"], errors="coerce").fillna(0.0).max())
                if not archetype_players.empty else 0.0
            )

    for side, players in [("off", team_off_players), ("def", team_def_players)]:
        raw = pd.to_numeric(players["raw"], errors="coerce").fillna(0.0).sort_values(ascending=False)
        profile[f"{side}_player_count"] = float(len(players))
        profile[f"{side}_top_player_raw"] = float(raw.iloc[0]) if not raw.empty else 0.0
        profile[f"{side}_top5_player_raw_sum"] = float(raw.head(5).sum()) if not raw.empty else 0.0
        profile[f"{side}_top10_player_raw_sum"] = float(raw.head(10).sum()) if not raw.empty else 0.0

    profile["roster_top_player_raw"] = max(profile["off_top_player_raw"], profile["def_top_player_raw"])
    profile["roster_top10_player_raw_sum"] = profile["off_top10_player_raw_sum"] + profile["def_top10_player_raw_sum"]
    return profile


def extract_archetype_flags(player_list):
    flags = {
        "has_dual_threat_qb": 0,
        "has_elite_receiver": 0,
        "has_lockdown_cb": 0,
        "has_star_rusher": 0,
        "has_route_runner": 0,
        "team_elite_archetype_count": 0
    }
    for player in player_list:
        label = player["label"].lower()
        pos = player["position"].lower()
        archetype = player["archetype"].lower()

        if "dual" in archetype and pos == "qb":
            flags["has_dual_threat_qb"] = 1
        if any(x in archetype for x in ["yac specialist", "deep threat", "route runner"]):
            if pos in ["wr", "te"]:
                flags["has_elite_receiver"] = 1
        if "lockdown corner" in archetype:
            flags["has_lockdown_cb"] = 1
        if any(x in archetype for x in ["disrupter", "closer"]):
            if pos in ["lb", "dl"]:
                flags["has_star_rusher"] = 1
        if "route runner" in archetype and pos == "wr":
            flags["has_route_runner"] = 1
        if any(x in archetype for x in ["elite", "lockdown", "disrupter", "closer"]):
            flags["team_elite_archetype_count"] += 1

    return flags


def build_feature_row(team_a, team_b, team_data):
    flags_a = extract_archetype_flags(team_data[team_a])
    flags_b = extract_archetype_flags(team_data[team_b])
    rating_data = load_rating_data()
    ratings_a = team_rating_profile(team_a, rating_data)
    ratings_b = team_rating_profile(team_b, rating_data)

    feature_row = {
        "team_a": team_a,
        "team_b": team_b,
    }
    for key, value in flags_a.items():
        feature_row[f"a_{key}"] = value
    for key, value in flags_b.items():
        feature_row[f"b_{key}"] = value

    for key, value in ratings_a.items():
        feature_row[f"a_{key}"] = value
    for key, value in ratings_b.items():
        feature_row[f"b_{key}"] = value
    for key in sorted(ratings_a):
        feature_row[f"diff_{key}"] = ratings_a[key] - ratings_b[key]

    feature_row.update({
        "a_offense_vs_b_defense": ratings_a["off_total_rating"] - ratings_b["def_total_rating"],
        "b_offense_vs_a_defense": ratings_b["off_total_rating"] - ratings_a["def_total_rating"],
        "a_rush_off_vs_b_run_def": ratings_a["off_rushing_rating"] - ratings_b["def_rushing_rating"],
        "b_rush_off_vs_a_run_def": ratings_b["off_rushing_rating"] - ratings_a["def_rushing_rating"],
        "a_pass_off_vs_b_pass_def": ratings_a["off_passing_rating"] - ratings_b["def_passing_rating"],
        "b_pass_off_vs_a_pass_def": ratings_b["off_passing_rating"] - ratings_a["def_passing_rating"],
        "a_score_off_vs_b_score_def": ratings_a["off_scoring_rating"] - ratings_b["def_scoring_rating"],
        "b_score_off_vs_a_score_def": ratings_b["off_scoring_rating"] - ratings_a["def_scoring_rating"],
        "a_qb_vs_b_secondary": ratings_a["off_qb_top_raw"] - ratings_b["def_cb_top_raw"],
        "b_qb_vs_a_secondary": ratings_b["off_qb_top_raw"] - ratings_a["def_cb_top_raw"],
        "a_wr_vs_b_cb": ratings_a["off_wr_top3_raw_mean"] - ratings_b["def_cb_top3_raw_mean"],
        "b_wr_vs_a_cb": ratings_b["off_wr_top3_raw_mean"] - ratings_a["def_cb_top3_raw_mean"],
        "a_te_vs_b_safety": ratings_a["off_te_top3_raw_mean"] - ratings_b["def_s_top3_raw_mean"],
        "b_te_vs_a_safety": ratings_b["off_te_top3_raw_mean"] - ratings_a["def_s_top3_raw_mean"],
        "a_run_game_vs_b_front": ratings_a["off_rb_top3_raw_mean"] + ratings_a["off_ol_top_raw"] - ratings_b["def_dl_top3_raw_mean"] - ratings_b["def_lb_top3_raw_mean"],
        "b_run_game_vs_a_front": ratings_b["off_rb_top3_raw_mean"] + ratings_b["off_ol_top_raw"] - ratings_a["def_dl_top3_raw_mean"] - ratings_a["def_lb_top3_raw_mean"],
        "a_pass_pro_vs_b_rush": ratings_a["off_ol_top_raw"] - ratings_b["def_dl_top3_raw_mean"] - ratings_b["def_lb_top3_raw_mean"],
        "b_pass_pro_vs_a_rush": ratings_b["off_ol_top_raw"] - ratings_a["def_dl_top3_raw_mean"] - ratings_a["def_lb_top3_raw_mean"],
    })

    return feature_row


def generate_synthetic_training_set():
    team_data = inject_all_teams()
    features = []
    labels = []

    for team_a, team_b in itertools.permutations(team_data.keys(), 2):
        feature_row = build_feature_row(team_a, team_b, team_data)

        # Synthetic baseline for experiments only. This target is deterministic
        # and will produce overconfident probabilities if used for production.
        label = int(
            feature_row["a_team_elite_archetype_count"]
            >= feature_row["b_team_elite_archetype_count"]
        )
        features.append(feature_row)
        labels.append(label)

    X = pd.DataFrame(features)
    y = pd.Series(labels, name="team_a_wins")
    return X, y


def generate_training_set():
    team_data = inject_all_teams()
    schedule = get_schedule_df().dropna(subset=["Winner/tie", "Loser/tie"])
    features = []
    labels = []

    for _, game in schedule.iterrows():
        winner = TEAM_NAME_ALIASES.get(str(game["Winner/tie"]).strip())
        loser = TEAM_NAME_ALIASES.get(str(game["Loser/tie"]).strip())

        if winner not in team_data or loser not in team_data:
            continue

        features.append(build_feature_row(winner, loser, team_data))
        labels.append(1)
        features.append(build_feature_row(loser, winner, team_data))
        labels.append(0)

    if not features:
        raise ValueError("No usable schedule rows found for RF training.")

    X = pd.DataFrame(features)
    y = pd.Series(labels, name="team_a_wins")
    return X, y


if __name__ == "__main__":
    X, y = generate_training_set()
    print("Training set size:", X.shape)
    print(X.head())

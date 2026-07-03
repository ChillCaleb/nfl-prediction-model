from __future__ import annotations

import math
import os
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
RATING_DB = ROOT_DIR / "Database" / "nfl_ratings.db"
PLAYER_DB = ROOT_DIR / "Database" / "nfl_player_data.db"
SCHEDULE_CSV = ROOT_DIR / "Legacy_Files" / "NFL" / "raw_data" / "Full_Schedule.csv"
TEAM_STAT_DIR = ROOT_DIR / "Legacy_Files" / "NFL" / "raw_data"
MODEL_PATH = ROOT_DIR / "Model" / "rf_matchup_model.joblib"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Several legacy modules use project-relative paths. Keep Streamlit launches
# from other working directories pointed at the project root.
os.chdir(ROOT_DIR)

from Legacy_Files.Engine.constants import abbr_to_full, full_to_abbr, team_name_alias
from probability_models import MODEL_REGISTRY, logistic_win_probability
from groq_utils import get_groq_api_keys, get_groq_model, post_groq_chat_completion


DISPLAY_PROBABILITY_FLOOR = 0.005
OFFENSIVE_POSITIONS = {"QB", "RB", "WR", "TE", "OL"}
POSITION_GROUPS = {
    "QB": {"QB"},
    "RB": {"RB", "R"},
    "WR": {"WR", "W"},
    "TE": {"TE"},
    "OL": {"OL", "LT", "RT", "G", "LG", "RG", "C"},
    "DL": {"D", "DL", "DE", "DT", "EDGE", "NT", "LE", "RE", "LDE", "RDE"},
    "LB": {"L", "LB", "MLB", "ILB", "OLB", "WLB", "SLB", "LOLB", "ROLB"},
    "CB": {"C", "CB", "DB", "LCB", "RCB"},
    "S": {"S", "SS", "FS"},
    "DB": {"C", "CB", "DB", "LCB", "RCB", "S", "SS", "FS"},
}

SLUG_TO_FULL = {
    team_name_alias[abbr]: full_name
    for abbr, full_name in abbr_to_full.items()
}
SLUG_TO_ABBR = {
    team_name_alias[abbr]: abbr
    for abbr in abbr_to_full
}
FULL_TO_SLUG = {
    full_name: team_name_alias[abbr]
    for full_name, abbr in full_to_abbr.items()
}


def _read_sql(db_path: Path, query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def _clean_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    return df


def bound_probability(probability: float, floor: float = DISPLAY_PROBABILITY_FLOOR) -> float:
    probability = float(probability)
    return min(max(probability, floor), 1 - floor)


def format_probability(probability: float, precision: int = 1) -> str:
    return f"{bound_probability(probability):.{precision}%}"


def display_team(team_slug: str) -> str:
    return SLUG_TO_FULL.get(str(team_slug).lower(), str(team_slug).replace("_", " ").title())


def _team_match_values(team: str) -> set[str]:
    team = normalize_team(team)
    full_name = display_team(team)
    nickname = full_name.split()[-1] if full_name else team
    abbr = SLUG_TO_ABBR.get(team, "")
    return {
        team.lower(),
        full_name.lower(),
        nickname.lower(),
        abbr.lower(),
    }


def get_team_options() -> list[str]:
    return sorted(load_team_ratings()["offense"].index.tolist(), key=display_team)


def normalize_team(value: str) -> str:
    value = str(value).strip()
    lowered = value.lower()
    if lowered in SLUG_TO_FULL:
        return lowered
    for full_name, slug in FULL_TO_SLUG.items():
        if value.lower() == full_name.lower():
            return slug
    raise ValueError(f"Unknown team: {value}")


def ai_available() -> bool:
    return bool(get_groq_api_keys())


@lru_cache(maxsize=256)
def _call_groq_cached(
    prompt: str,
    temperature: float,
    model: str,
    key_sources: tuple[str, ...],
) -> str:
    response, key_source = post_groq_chat_completion(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
        timeout=30,
    )
    try:
        content = response.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        raise RuntimeError(f"Groq returned an unexpected response: {response.text}") from exc
    return f"{content}\n\nSource: {key_source}"


def _call_groq(prompt: str, temperature: float = 0.45) -> str:
    api_keys = get_groq_api_keys()
    if not api_keys:
        return "AI summary unavailable because GROQ_API_KEY is not set."

    key_sources = tuple(source_name for source_name, _ in api_keys)
    return _call_groq_cached(prompt, float(temperature), get_groq_model(), key_sources)


@lru_cache(maxsize=1)
def load_team_ratings() -> dict[str, pd.DataFrame]:
    offense = _read_sql(RATING_DB, "SELECT * FROM Offensive_team_ratings")
    defense = _read_sql(RATING_DB, "SELECT * FROM Defensive_team_ratings")

    offense = _clean_numeric(offense, ["rushing", "passing", "scoring", "total"])
    defense = _clean_numeric(defense, ["rushing", "passing", "scoring", "total"])

    offense["team"] = offense["team"].astype(str).str.lower()
    defense["team"] = defense["team"].astype(str).str.lower()

    offense = offense.groupby("team", as_index=True).mean(numeric_only=True)
    defense = defense.groupby("team", as_index=True).mean(numeric_only=True)
    return {"offense": offense, "defense": defense}


@lru_cache(maxsize=1)
def load_player_ratings() -> pd.DataFrame:
    offense = _read_sql(
        RATING_DB,
        "SELECT player, team, pos, raw, normalized, archetype FROM Offensive_player_ratings",
    )
    defense = _read_sql(
        RATING_DB,
        """
        SELECT player, team, pos, raw, normalized, rushing, passing, scoring, archetype
        FROM Defensive_player_ratings
        """,
    )

    offense["side"] = "Offense"
    defense["side"] = "Defense"
    players = pd.concat([offense, defense], ignore_index=True, sort=False)
    players = _clean_numeric(players, ["raw", "normalized", "rushing", "passing", "scoring"])
    players["player"] = players["player"].astype(str).str.strip()
    players["team"] = players["team"].astype(str).str.lower().str.strip()
    players["pos"] = players["pos"].astype(str).str.upper().str.strip()
    players["archetype"] = players["archetype"].fillna("Unclassified").astype(str)
    players = players.drop_duplicates(subset=["player", "team", "pos", "side", "archetype"])
    players["team_name"] = players["team"].map(display_team)
    players = players.sort_values("raw", ascending=False).reset_index(drop=True)
    return players


@lru_cache(maxsize=1)
def load_player_stat_tables() -> dict[str, pd.DataFrame]:
    tables = [
        "passing",
        "advanced_passing",
        "rushing_and_receiving",
        "advanced_rushing",
        "advanced_receiving",
        "defense",
        "advanced_defense",
        "snap_counts",
    ]
    return {table: _read_sql(PLAYER_DB, f"SELECT * FROM {table}") for table in tables}


@lru_cache(maxsize=1)
def load_team_stat_tables() -> dict[str, pd.DataFrame]:
    stat_tables = {}
    for path in sorted(TEAM_STAT_DIR.glob("*.csv")):
        try:
            stat_tables[path.stem] = pd.read_csv(path)
        except Exception:
            continue
    return stat_tables


def _profile_table_name(name: str) -> str:
    return str(name).replace("_", " ").title()


def _clean_table_for_profile(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = cleaned.dropna(how="all")
    if "Tm" in cleaned.columns:
        cleaned = cleaned[cleaned["Tm"].astype(str).str.strip().str.lower() != "tm"]
    unnamed = [column for column in cleaned.columns if str(column).startswith("Unnamed")]
    if unnamed:
        cleaned = cleaned.drop(columns=unnamed)
    return cleaned.reset_index(drop=True)


def get_team_stat_tables(team: str) -> dict[str, pd.DataFrame]:
    team = normalize_team(team)
    match_values = _team_match_values(team)
    output = {}

    for table_name, table in load_team_stat_tables().items():
        table = _clean_table_for_profile(table)
        if table.empty:
            continue

        if table_name == "Full_Schedule":
            mask = pd.Series(False, index=table.index)
            for column in ["Winner/tie", "Loser/tie"]:
                if column in table.columns:
                    mask = mask | table[column].astype(str).str.strip().str.lower().isin(match_values)
            matches = table[mask]
        elif "Tm" in table.columns:
            matches = table[table["Tm"].astype(str).str.strip().str.lower().isin(match_values)]
        else:
            continue

        if not matches.empty:
            output[_profile_table_name(table_name)] = matches.reset_index(drop=True)

    return output


def search_players(
    query: str = "",
    team: str | None = None,
    position: str | None = None,
    side: str = "All",
    min_rating: float = 0.0,
    limit: int = 250,
) -> pd.DataFrame:
    players = load_player_ratings().copy()
    query = str(query).strip().lower()
    if query:
        players = players[players["player"].str.lower().str.contains(query, na=False)]
    if team and team != "All":
        players = players[players["team"] == normalize_team(team)]
    if position and position != "All":
        aliases = POSITION_GROUPS.get(position.upper(), {position.upper()})
        players = players[players["pos"].isin(aliases)]
    if side != "All":
        players = players[players["side"] == side]
    players = players[players["raw"] >= float(min_rating)]
    return players.head(limit).reset_index(drop=True)


def get_team_roster(
    team: str,
    position: str | None = None,
    side: str = "All",
    query: str = "",
    min_rating: float = 0.0,
) -> pd.DataFrame:
    team = normalize_team(team)
    roster = load_player_ratings()
    roster = roster[roster["team"] == team].copy()

    if position and position != "All":
        aliases = POSITION_GROUPS.get(position.upper(), {position.upper()})
        roster = roster[roster["pos"].isin(aliases)]
    if side != "All":
        roster = roster[roster["side"] == side]
    if query:
        roster = roster[roster["player"].str.lower().str.contains(str(query).strip().lower(), na=False)]
    roster = roster[roster["raw"] >= float(min_rating)]
    side_order = {"Offense": 0, "Defense": 1}
    roster = roster.assign(_side_order=roster["side"].map(side_order).fillna(2))
    roster = roster.sort_values(["_side_order", "raw", "player"], ascending=[True, False, True])
    return roster.drop(columns=["_side_order"]).reset_index(drop=True)


def _match_stat_rows(player_name: str, team: str | None = None) -> dict[str, pd.DataFrame]:
    matches: dict[str, pd.DataFrame] = {}
    player_lower = str(player_name).strip().lower()
    team_values = _team_match_values(team) if team else set()
    for table_name, table in load_player_stat_tables().items():
        if "Player" not in table.columns:
            continue
        table_matches = table[table["Player"].astype(str).str.lower() == player_lower]
        if not table_matches.empty:
            if team_values and "Team" in table_matches.columns:
                team_matches = table_matches[
                    table_matches["Team"].astype(str).str.strip().str.lower().isin(team_values)
                ]
                if not team_matches.empty:
                    table_matches = team_matches
            matches[table_name] = table_matches.reset_index(drop=True)
    return matches


def get_player_profile(player_name: str, team: str | None = None, include_ai: bool = False) -> dict[str, Any]:
    player_lower = str(player_name).strip().lower()
    ratings = load_player_ratings()
    rating_rows = ratings[ratings["player"].str.lower() == player_lower].copy()

    if rating_rows.empty:
        rating_rows = ratings[
            ratings["player"].str.lower().str.contains(player_lower, na=False)
        ].copy()

    if team:
        normalized_team = normalize_team(team)
        team_rows = rating_rows[rating_rows["team"] == normalized_team]
        if not team_rows.empty:
            rating_rows = team_rows

    stat_rows = _match_stat_rows(player_name, team=team)
    ai_blurb = None
    if include_ai:
        ai_blurb = generate_player_ai_summary(player_name, normalize_team(team) if team else None)

    return {
        "ratings": rating_rows.sort_values("raw", ascending=False).reset_index(drop=True),
        "stat_rows": stat_rows,
        "ai_blurb": ai_blurb,
    }


def get_team_profile(team: str) -> dict[str, Any]:
    team = normalize_team(team)
    ratings = load_team_ratings()
    if team not in ratings["offense"].index or team not in ratings["defense"].index:
        raise ValueError(f"Team '{team}' was not found in the ratings database.")

    off = ratings["offense"].loc[team].to_dict()
    defense = ratings["defense"].loc[team].to_dict()
    return {
        "team": team,
        "display": display_team(team),
        "offense": off,
        "defense": defense,
        "overall_sum": float(off.get("total", 0.0) + defense.get("total", 0.0)),
        "overall_blend": float(0.5 * off.get("total", 0.0) + 0.5 * defense.get("total", 0.0)),
    }


def get_team_breakdown(team: str, include_ai: bool = False) -> dict[str, Any]:
    team = normalize_team(team)
    profile = get_team_profile(team)
    players = load_player_ratings()
    team_players = players[players["team"] == team].copy()
    offense = team_players[team_players["side"] == "Offense"]
    defense = team_players[team_players["side"] == "Defense"]

    top_offense = (
        offense[offense["raw"] > 0]
        .drop_duplicates("player")
        .sort_values("raw", ascending=False)
        .head(8)
        .reset_index(drop=True)
    )
    top_defense = (
        defense[defense["raw"] > 0]
        .drop_duplicates("player")
        .sort_values("raw", ascending=False)
        .head(8)
        .reset_index(drop=True)
    )
    position_units = (
        team_players.groupby(["pos", "side"], as_index=False)
        .agg(players=("player", "nunique"), avg_rating=("raw", "mean"), top_rating=("raw", "max"))
        .sort_values("avg_rating", ascending=False)
        .reset_index(drop=True)
    )

    room_counts = pd.concat([top_offense["pos"], top_defense["pos"]]).value_counts()
    prominent_room = room_counts.index[0] if not room_counts.empty else "N/A"
    stat_tables = get_team_stat_tables(team)

    ai_summary = None
    if include_ai:
        ai_summary = generate_team_profile_summary(team)

    return {
        "profile": profile,
        "top_offense": top_offense,
        "top_defense": top_defense,
        "position_units": position_units,
        "prominent_room": prominent_room,
        "stat_tables": stat_tables,
        "ai_summary": ai_summary,
    }


def get_position_room(team: str, position: str, include_ai: bool = False) -> dict[str, Any]:
    team = normalize_team(team)
    position = position.upper()
    aliases = POSITION_GROUPS.get(position, {position})
    players = load_player_ratings()
    room = players[(players["team"] == team) & (players["pos"].isin(aliases))].copy()
    room = room.drop_duplicates("player").sort_values("raw", ascending=False).reset_index(drop=True)

    summary = {
        "players": int(room["player"].nunique()) if not room.empty else 0,
        "avg_rating": float(room["raw"].mean()) if not room.empty else 0.0,
        "top_rating": float(room["raw"].max()) if not room.empty else 0.0,
    }

    ai_summary = None
    if include_ai:
        ai_summary = generate_room_ai_summary(team, position, room)

    return {"room": room, "summary": summary, "ai_summary": ai_summary}


def _unit_advantage_prob(offense_rating: float, defense_rating: float, scale: float = 15.0) -> float:
    delta = float(offense_rating) - float(defense_rating)
    return 1 / (1 + 10 ** (-delta / scale))


def _matchup_win_probability(team1_total: float, team2_total: float, scale: float = 20.0) -> float:
    return 1 / (1 + 10 ** ((team2_total - team1_total) / scale))


def simulate_rating_matchup(team_a: str, team_b: str, include_ai: bool = False) -> dict[str, Any]:
    team_a = normalize_team(team_a)
    team_b = normalize_team(team_b)
    profile_a = get_team_profile(team_a)
    profile_b = get_team_profile(team_b)

    prob_a = bound_probability(
        _matchup_win_probability(profile_a["overall_sum"], profile_b["overall_sum"])
    )
    winner = team_a if prob_a >= 0.5 else team_b
    units = pd.DataFrame(
        [
            {
                "Unit": f"{display_team(team_a)} rush offense vs {display_team(team_b)} run defense",
                "Advantage": _unit_advantage_prob(
                    profile_a["offense"]["rushing"], profile_b["defense"]["rushing"]
                ),
            },
            {
                "Unit": f"{display_team(team_a)} pass offense vs {display_team(team_b)} pass defense",
                "Advantage": _unit_advantage_prob(
                    profile_a["offense"]["passing"], profile_b["defense"]["passing"]
                ),
            },
            {
                "Unit": f"{display_team(team_a)} scoring vs {display_team(team_b)} scoring defense",
                "Advantage": _unit_advantage_prob(
                    profile_a["offense"]["scoring"], profile_b["defense"]["scoring"]
                ),
            },
            {
                "Unit": f"{display_team(team_b)} rush offense vs {display_team(team_a)} run defense",
                "Advantage": _unit_advantage_prob(
                    profile_b["offense"]["rushing"], profile_a["defense"]["rushing"]
                ),
            },
            {
                "Unit": f"{display_team(team_b)} pass offense vs {display_team(team_a)} pass defense",
                "Advantage": _unit_advantage_prob(
                    profile_b["offense"]["passing"], profile_a["defense"]["passing"]
                ),
            },
            {
                "Unit": f"{display_team(team_b)} scoring vs {display_team(team_a)} scoring defense",
                "Advantage": _unit_advantage_prob(
                    profile_b["offense"]["scoring"], profile_a["defense"]["scoring"]
                ),
            },
        ]
    )
    units["Advantage %"] = units["Advantage"].map(lambda value: round(value * 100, 1))

    ai_summary = None
    if include_ai:
        ai_summary = generate_rating_matchup_ai_summary(team_a, team_b, prob_a, units)

    return {
        "team_a": team_a,
        "team_b": team_b,
        "winner": winner,
        "probability_a": prob_a,
        "probability_b": bound_probability(1 - prob_a),
        "profile_a": profile_a,
        "profile_b": profile_b,
        "units": units,
        "ai_summary": ai_summary,
    }


@lru_cache(maxsize=1)
def _load_team_vectors() -> dict[str, list[dict[str, Any]]]:
    from player_injection import inject_all_teams

    return inject_all_teams()


@lru_cache(maxsize=1)
def _load_rf_model() -> Any:
    import joblib

    return joblib.load(MODEL_PATH)


def simulate_ml_matchup(team_a: str, team_b: str, include_ai: bool = False) -> dict[str, Any]:
    team_a = normalize_team(team_a)
    team_b = normalize_team(team_b)
    team_data = _load_team_vectors()
    if team_a not in team_data or team_b not in team_data:
        raise ValueError("One or both teams were not found in the injected roster vectors.")

    from AI_simulate import (
        build_feature_row,
        build_matchup_context,
        conditional_insights,
        rating_edge_prob,
    )

    model = _load_rf_model()
    feature_row, flags_a, flags_b = build_feature_row(team_a, team_b, team_data)
    x_model = feature_row.drop(columns=["team_a", "team_b"])
    prediction = model.predict(x_model)[0]
    classes = list(getattr(model, "classes_", [0, 1]))
    class_index = classes.index(prediction) if prediction in classes else int(prediction)
    probability = bound_probability(model.predict_proba(x_model)[0][class_index])
    predicted_team = team_a if int(prediction) == 1 else team_b

    features = x_model.iloc[0]
    rush_edge = rating_edge_prob(features["a_run_game_vs_b_front"], scale=60)
    pass_edge = rating_edge_prob(features["a_pass_off_vs_b_pass_def"], scale=35)
    separation_edge = rating_edge_prob(features["a_wr_vs_b_cb"], scale=45)
    insights = conditional_insights(flags_a, flags_b, team_a, team_b, features)

    feature_edges = pd.DataFrame(
        [
            ["Total rating edge", features.get("diff_team_total_rating", 0.0)],
            ["Pass offense vs pass defense", features.get("a_pass_off_vs_b_pass_def", 0.0)],
            ["Opponent pass offense vs pass defense", features.get("b_pass_off_vs_a_pass_def", 0.0)],
            ["WR/TE vs corners", features.get("a_wr_vs_b_cb", 0.0)],
            ["Opponent WR/TE vs corners", features.get("b_wr_vs_a_cb", 0.0)],
            ["Run game vs front", features.get("a_run_game_vs_b_front", 0.0)],
            ["Opponent run game vs front", features.get("b_run_game_vs_a_front", 0.0)],
            ["Pass protection vs rush", features.get("a_pass_pro_vs_b_rush", 0.0)],
            ["Opponent pass protection vs rush", features.get("b_pass_pro_vs_a_rush", 0.0)],
        ],
        columns=["Feature", "Edge"],
    )
    feature_edges["Edge"] = pd.to_numeric(feature_edges["Edge"], errors="coerce").fillna(0.0)

    ai_summary = None
    if include_ai:
        analyst_context = build_matchup_context(team_a, team_b, team_data, features)
        ai_summary = generate_ml_matchup_ai_summary(
            team_a,
            team_b,
            predicted_team,
            probability,
            rush_edge,
            pass_edge,
            separation_edge,
            insights,
            analyst_context,
        )

    return {
        "team_a": team_a,
        "team_b": team_b,
        "winner": predicted_team,
        "confidence": probability,
        "rush_edge": bound_probability(rush_edge),
        "pass_edge": bound_probability(pass_edge),
        "separation_edge": bound_probability(separation_edge),
        "insights": insights,
        "feature_edges": feature_edges,
        "feature_row": x_model,
        "ai_summary": ai_summary,
    }


def _season_team_rating(full_team_name: str) -> float | None:
    team = FULL_TO_SLUG.get(str(full_team_name).strip())
    if not team:
        return None
    return get_team_profile(team)["overall_blend"]


def _season_game_probability(model_name: str, rating_a: float, rating_b: float) -> float:
    model_func = MODEL_REGISTRY.get(model_name)
    if model_func is None:
        raise ValueError(f"Unknown model: {model_name}")

    if model_name == "outperform":
        return float(model_func(rating_a, rating_b, pd.Series([rating_a, rating_b])))
    if model_name == "bayesian":
        prior = 0.5
        likelihood = logistic_win_probability(rating_a - rating_b)
        return float(model_func(prior, likelihood, 1.0))
    if model_name == "elo_expected":
        return float(model_func(rating_a, rating_b))
    return float(model_func(rating_a - rating_b))


def simulate_single_season(
    model_name: str = "outperform",
    seed: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    schedule = pd.read_csv(SCHEDULE_CSV).dropna(subset=["Winner/tie", "Loser/tie"])
    rng = np.random.default_rng(seed)

    teams = sorted(pd.unique(schedule[["Winner/tie", "Loser/tie"]].values.ravel()))
    wins = {team: 0 for team in teams}
    losses = {team: 0 for team in teams}
    game_rows: list[dict[str, Any]] = []

    for _, game in schedule.iterrows():
        team_a = str(game["Winner/tie"]).strip()
        team_b = str(game["Loser/tie"]).strip()
        rating_a = _season_team_rating(team_a)
        rating_b = _season_team_rating(team_b)
        if rating_a is None or rating_b is None:
            continue

        prob_a = bound_probability(_season_game_probability(model_name, rating_a, rating_b))
        winner = team_a if rng.random() < prob_a else team_b
        loser = team_b if winner == team_a else team_a
        wins[winner] += 1
        losses[loser] += 1

        game_rows.append(
            {
                "Week": game.get("Week"),
                "Team A": team_a,
                "Team B": team_b,
                "Team A Win %": round(prob_a * 100, 1),
                "Simulated Winner": winner,
            }
        )

    standings = (
        pd.DataFrame({"Team": list(wins.keys()), "Wins": list(wins.values()), "Losses": list(losses.values())})
        .sort_values(["Wins", "Losses", "Team"], ascending=[False, True, True])
        .reset_index(drop=True)
    )
    standings.insert(0, "Rank", range(1, len(standings) + 1))
    return standings, pd.DataFrame(game_rows)


def simulate_many_seasons(
    model_name: str = "outperform",
    runs: int = 1,
    seed: int | None = None,
) -> dict[str, pd.DataFrame]:
    runs = max(1, int(runs))
    base_rng = np.random.default_rng(seed)
    all_standings: list[pd.DataFrame] = []
    last_standings = pd.DataFrame()
    last_games = pd.DataFrame()

    for run_index in range(runs):
        run_seed = int(base_rng.integers(0, 2**32 - 1))
        standings, games = simulate_single_season(model_name, run_seed)
        standings = standings.copy()
        standings["Run"] = run_index + 1
        standings["First Place"] = standings["Rank"] == 1
        all_standings.append(standings)
        last_standings = standings.drop(columns=["Run", "First Place"])
        last_games = games

    combined = pd.concat(all_standings, ignore_index=True)
    summary = (
        combined.groupby("Team", as_index=False)
        .agg(
            avg_wins=("Wins", "mean"),
            avg_losses=("Losses", "mean"),
            best_wins=("Wins", "max"),
            worst_wins=("Wins", "min"),
            avg_rank=("Rank", "mean"),
            first_place_rate=("First Place", "mean"),
        )
        .sort_values(["avg_wins", "avg_rank"], ascending=[False, True])
        .reset_index(drop=True)
    )
    summary.insert(0, "Rank", range(1, len(summary) + 1))
    summary["avg_wins"] = summary["avg_wins"].round(2)
    summary["avg_losses"] = summary["avg_losses"].round(2)
    summary["avg_rank"] = summary["avg_rank"].round(2)
    summary["first_place_rate"] = (summary["first_place_rate"] * 100).round(1)

    return {
        "summary": summary,
        "last_standings": last_standings,
        "last_games": last_games,
        "all_standings": combined,
    }


def _table_to_prompt(df: pd.DataFrame, limit: int = 3) -> str:
    if df.empty:
        return "No rows."
    rows = []
    for row in df.head(limit).to_dict("records"):
        values = [
            f"{column}: {value}"
            for column, value in row.items()
            if pd.notna(value) and str(value).strip() != ""
        ]
        rows.append("; ".join(values))
    return "\n".join(rows)


def _rating_rows_to_prompt(ratings: pd.DataFrame) -> str:
    if ratings.empty:
        return "No model ratings found."
    columns = [
        "player",
        "team_name",
        "side",
        "pos",
        "raw",
        "normalized",
        "rushing",
        "passing",
        "scoring",
        "archetype",
    ]
    available = [column for column in columns if column in ratings.columns]
    return _table_to_prompt(ratings[available], limit=8)


@lru_cache(maxsize=256)
def generate_player_ai_summary(player_name: str, team: str | None = None) -> str:
    profile = get_player_profile(player_name, team=team, include_ai=False)
    ratings = profile["ratings"]
    stat_rows = profile["stat_rows"]
    team_context = f" for the {display_team(team)}" if team else ""

    stat_blocks = []
    for table_name, table in stat_rows.items():
        stat_blocks.append(f"{_profile_table_name(table_name)}:\n{_table_to_prompt(table, limit=2)}")
    stats = "\n\n".join(stat_blocks) if stat_blocks else "No raw stat rows found."

    prompt = f"""
Write a profile summary for NFL player {player_name}{team_context}.

Model ratings:
{_rating_rows_to_prompt(ratings)}

Raw and advanced stat rows:
{stats}

Use the player's real ratings and stats only. Start with the player's role and archetype, then explain the strongest traits, limitations, usage, and why the model values them.
Do not invent teams, players, injuries, or awards. Keep it engaging and specific in 2-4 concise paragraphs.
"""
    try:
        return _call_groq(prompt, temperature=0.45)
    except Exception as exc:
        return f"AI player summary failed: {exc}"


@lru_cache(maxsize=128)
def generate_team_profile_summary(team: str) -> str:
    team = normalize_team(team)
    profile = get_team_profile(team)
    players = load_player_ratings()
    team_players = players[players["team"] == team].copy()
    top_offense = (
        team_players[(team_players["side"] == "Offense") & (team_players["raw"] > 0)]
        .drop_duplicates("player")
        .sort_values("raw", ascending=False)
        .head(8)
    )
    top_defense = (
        team_players[(team_players["side"] == "Defense") & (team_players["raw"] > 0)]
        .drop_duplicates("player")
        .sort_values("raw", ascending=False)
        .head(8)
    )
    stat_tables = get_team_stat_tables(team)
    return generate_team_ai_summary(profile, top_offense, top_defense, stat_tables)


def generate_team_ai_summary(
    profile: dict[str, Any],
    top_offense: pd.DataFrame,
    top_defense: pd.DataFrame,
    stat_tables: dict[str, pd.DataFrame] | None = None,
) -> str:
    off_players = "\n".join(
        f"- {row.player} ({row.pos}): {row.archetype}"
        for row in top_offense.itertuples()
    )
    def_players = "\n".join(
        f"- {row.player} ({row.pos}): {row.archetype}"
        for row in top_defense.itertuples()
    )
    stat_tables = stat_tables or {}
    stat_blocks = []
    for table_name, table in stat_tables.items():
        if table_name == "Full Schedule":
            continue
        stat_blocks.append(f"{table_name}:\n{_table_to_prompt(table, limit=2)}")
    stats = "\n\n".join(stat_blocks) if stat_blocks else "No raw team stat rows found."

    prompt = f"""
Write a concise NFL team profile summary for the {profile['display']}.

Model offensive ratings:
{profile['offense']}

Model defensive ratings:
{profile['defense']}

Top offensive contributors:
{off_players}

Top defensive contributors:
{def_players}

Raw team stat rows:
{stats}

Focus on identity, strengths, weak points, player groups that drive the profile, and how the model sees this team.
Use only the supplied players and stats. Do not invent players, injuries, or transactions. Write in 3-4 tight paragraphs.
"""
    try:
        return _call_groq(prompt)
    except Exception as exc:
        return f"AI team summary failed: {exc}"


def generate_room_ai_summary(team: str, position: str, room: pd.DataFrame) -> str:
    team_name = display_team(team)
    if room.empty:
        return f"No {position} room data is available for {team_name}."

    top_players = "\n".join(
        f"- {row.player} ({row.pos}): {row.archetype}, raw rating {row.raw:.1f}"
        for row in room.head(8).itertuples()
    )
    prompt = f"""
Write a positional room breakdown for the {team_name} {position} group.

Players:
{top_players}

Explain the unit identity, depth, standout traits, and matchup implications.
Do not invent players. Do not use bullets. Write 2-3 paragraphs.
"""
    try:
        return _call_groq(prompt)
    except Exception as exc:
        return f"AI room summary failed: {exc}"


def generate_rating_matchup_ai_summary(
    team_a: str,
    team_b: str,
    probability_a: float,
    units: pd.DataFrame,
) -> str:
    unit_lines = "\n".join(
        f"- {row['Unit']}: {row['Advantage %']:.1f}%"
        for _, row in units.iterrows()
    )
    prompt = f"""
Write an NFL matchup preview for {display_team(team_a)} vs {display_team(team_b)}.

Ratings model win probability:
{display_team(team_a)} {format_probability(probability_a)}
{display_team(team_b)} {format_probability(1 - probability_a)}

Unit edges:
{unit_lines}

Explain both paths to winning and name the strongest matchup levers.
Use a confident analyst tone, no bullets, 3-5 paragraphs.
"""
    try:
        return _call_groq(prompt)
    except Exception as exc:
        return f"AI ratings matchup summary failed: {exc}"


def generate_ml_matchup_ai_summary(
    team_a: str,
    team_b: str,
    predicted_team: str,
    confidence: float,
    rush_edge: float,
    pass_edge: float,
    separation_edge: float,
    insights: list[str],
    analyst_context: str,
) -> str:
    insights_block = "\n".join(f"- {insight}" for insight in insights) or "- No major conditional edge detected."
    prompt = f"""
Matchup: {display_team(team_a)} vs {display_team(team_b)}
ML prediction: {display_team(predicted_team)} with {format_probability(confidence)} confidence

Unit estimates for {display_team(team_a)}:
- Rush edge: {format_probability(rush_edge)}
- Pass edge: {format_probability(pass_edge)}
- Receiver separation edge: {format_probability(separation_edge)}

Conditional insights:
{insights_block}

Scouting packet:
{analyst_context}

Write a detailed NFL analyst-style matchup preview.
Use specific player names from the scouting packet and do not invent players.
Cover both paths to winning, then explain why the model picked {display_team(predicted_team)}.
Write 5-7 tight paragraphs with no bullets.
"""
    try:
        return _call_groq(prompt, temperature=0.5)
    except Exception as exc:
        return f"AI ML matchup summary failed: {exc}"

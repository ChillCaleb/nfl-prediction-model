import joblib
import math
import pandas as pd
from player_injection import inject_all_teams
from train_rf_data import build_feature_row as build_model_feature_row, extract_archetype_flags
import time
from groq_utils import get_groq_api_keys, get_groq_model, post_groq_chat_completion

MODEL_PATH = "Model/rf_matchup_model.joblib"
GROQ_MODEL = get_groq_model()
DISPLAY_PROBABILITY_FLOOR = 0.005
OFFENSIVE_POSITIONS = {"QB", "RB", "WR", "TE", "OL"}
POSITION_GROUPS = {
    "quarterbacks": {"QB"},
    "backs": {"RB"},
    "receivers": {"WR", "TE"},
    "offensive_line": {"OL"},
    "corners": {"C", "CB", "DB", "LCB", "RCB"},
    "safeties": {"S", "SS", "FS"},
    "front": {"D", "DL", "DE", "DT", "EDGE", "NT", "LE", "RE", "LDE", "RDE", "L", "LB", "MLB", "ILB", "OLB", "WLB", "SLB", "LOLB", "ROLB"},
}


def bound_probability(probability, floor=DISPLAY_PROBABILITY_FLOOR):
    probability = float(probability)
    return min(max(probability, floor), 1 - floor)


def format_probability(probability, precision=2):
    return f"{bound_probability(probability):.{precision}%}"

def unit_advantage_prob(team_flag, opp_flag, weight=0.5):
    return 0.55 if team_flag and not opp_flag else 0.5 if team_flag and opp_flag else 0.45 if not team_flag and opp_flag else 0.5

def rating_edge_prob(edge, scale=35):
    return 1 / (1 + math.exp(-float(edge) / scale))


def feature_value(features, key):
    if features is None or key not in features:
        return 0.0
    return float(features[key])


def conditional_insights(flags_a, flags_b, team_a, team_b, features=None):
    insights = []
    a_pass_edge = feature_value(features, "a_pass_off_vs_b_pass_def")
    b_pass_edge = feature_value(features, "b_pass_off_vs_a_pass_def")
    a_wr_edge = feature_value(features, "a_wr_vs_b_cb")
    b_wr_edge = feature_value(features, "b_wr_vs_a_cb")
    a_run_edge = feature_value(features, "a_run_game_vs_b_front")
    b_run_edge = feature_value(features, "b_run_game_vs_a_front")
    a_protection_edge = feature_value(features, "a_pass_pro_vs_b_rush")
    b_protection_edge = feature_value(features, "b_pass_pro_vs_a_rush")

    if a_pass_edge >= 8:
        insights.append(f"{team_a.upper()} has a measurable passing-game edge against {team_b.upper()}'s pass defense.")
    if b_pass_edge >= 8:
        insights.append(f"{team_b.upper()} has a measurable passing-game edge against {team_a.upper()}'s pass defense.")
    if a_wr_edge >= 10:
        insights.append(f"{team_a.upper()} receivers have a rating edge over {team_b.upper()}'s corner group.")
    if b_wr_edge >= 10:
        insights.append(f"{team_b.upper()} receivers have a rating edge over {team_a.upper()}'s corner group.")
    if a_run_edge >= 25:
        insights.append(f"The {team_a.upper()} run game and line match up well against the {team_b.upper()} front.")
    if b_run_edge >= 25:
        insights.append(f"The {team_b.upper()} run game and line match up well against the {team_a.upper()} front.")
    if a_protection_edge <= -15:
        insights.append(f"The {team_a.upper()} pass protection is a pressure risk against the {team_b.upper()} rush profile.")
    if b_protection_edge <= -15:
        insights.append(f"The {team_b.upper()} pass protection is a pressure risk against the {team_a.upper()} rush profile.")

    if not insights and flags_b["team_elite_archetype_count"] < flags_a["team_elite_archetype_count"]:
        insights.append(f"{team_a.upper()} carries the stronger high-impact archetype profile.")
    return insights

def slow_print(text, delay=0.04):
    for word in text.split():
        print(word, end=' ', flush=True)
        time.sleep(delay)
    print()

def dedupe_players(players):
    seen = set()
    unique = []
    for player in players:
        key = (
            player.get("name", "").strip().lower(),
            player.get("position", "").strip().upper(),
            player.get("archetype", "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(player)
    return unique


def top_players(players, positions=None, limit=5):
    unique = dedupe_players(players)
    if positions:
        positions = {position.upper() for position in positions}
        unique = [
            player for player in unique
            if player.get("position", "").upper() in positions
        ]

    return sorted(
        unique,
        key=lambda player: float(player.get("raw") or 0.0),
        reverse=True,
    )[:limit]


def format_player(player):
    raw = float(player.get("raw") or 0.0)
    return f"{player['name']} ({player['position']}, {player['archetype']}, rating {raw:.1f})"


def format_player_group(players):
    if not players:
        return "None identified"
    return "; ".join(format_player(player) for player in players)


def build_team_context(team, players):
    offense = top_players(players, OFFENSIVE_POSITIONS, limit=7)
    defense = top_players(
        players,
        POSITION_GROUPS["corners"] | POSITION_GROUPS["safeties"] | POSITION_GROUPS["front"],
        limit=7,
    )

    lines = [
        f"{team.upper()} top offense: {format_player_group(offense)}",
        f"{team.upper()} top defense: {format_player_group(defense)}",
    ]
    for group_name in ["quarterbacks", "backs", "receivers", "offensive_line", "corners", "safeties", "front"]:
        group_players = top_players(players, POSITION_GROUPS[group_name], limit=4)
        lines.append(f"{team.upper()} {group_name.replace('_', ' ')}: {format_player_group(group_players)}")

    return "\n".join(lines)


def build_matchup_context(team_a, team_b, team_data, features):
    context = [
        build_team_context(team_a, team_data[team_a]),
        build_team_context(team_b, team_data[team_b]),
        "",
        "Rating edges from the model feature row:",
        f"- {team_a.upper()} total team rating edge: {feature_value(features, 'diff_team_total_rating'):.1f}",
        f"- {team_a.upper()} passing offense vs {team_b.upper()} pass defense: {feature_value(features, 'a_pass_off_vs_b_pass_def'):.1f}",
        f"- {team_b.upper()} passing offense vs {team_a.upper()} pass defense: {feature_value(features, 'b_pass_off_vs_a_pass_def'):.1f}",
        f"- {team_a.upper()} WR/TE group vs {team_b.upper()} corners: {feature_value(features, 'a_wr_vs_b_cb'):.1f}",
        f"- {team_b.upper()} WR/TE group vs {team_a.upper()} corners: {feature_value(features, 'b_wr_vs_a_cb'):.1f}",
        f"- {team_a.upper()} run game and OL vs {team_b.upper()} front: {feature_value(features, 'a_run_game_vs_b_front'):.1f}",
        f"- {team_b.upper()} run game and OL vs {team_a.upper()} front: {feature_value(features, 'b_run_game_vs_a_front'):.1f}",
        f"- {team_a.upper()} pass protection vs {team_b.upper()} rush: {feature_value(features, 'a_pass_pro_vs_b_rush'):.1f}",
        f"- {team_b.upper()} pass protection vs {team_a.upper()} rush: {feature_value(features, 'b_pass_pro_vs_a_rush'):.1f}",
    ]
    return "\n".join(context)


def send_groq_summary(team_a, team_b, predicted_team, proba, rush, passthrow, sep, insights, analyst_context):
    if not get_groq_api_keys():
        print("❌ GROQ_API_KEY not found. Add it to .env, or set GROQ_API_KEY_FALLBACK / GROQ_API_KEYS.")
        return

    insights_block = "\n".join(["- " + i for i in insights])
    confidence = format_probability(proba)
    prompt = f"""
Matchup: {team_a} vs {team_b}
ML Prediction: {predicted_team} (confidence {confidence})

Unit Probabilities:
- Rush Success: {int(rush * 100)}%
- Pass Success: {int(passthrow * 100)}%
- WR Separation: {int(sep * 100)}%

Conditional What-Ifs:
{insights_block}

Scouting Packet:
{analyst_context}

Write a detailed NFL analyst-style matchup preview.
- Use specific player names from the scouting packet; do not invent players.
- Explain how the personnel creates the matchup, not just who has the edge.
- Cover both teams' paths to winning before explaining why the model picked {predicted_team}.
- Discuss at least one trench matchup, one coverage/pass-game matchup, and one player who can swing the game.
- If the confidence is modest, frame it as a close game instead of forcing certainty.
- Write in 5-7 tight paragraphs with a confident sports-broadcast tone. No bullets.
"""

    try:
        res, key_source = post_groq_chat_completion({
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
        })
    except RuntimeError as exc:
        print(f"❌ Error generating Groq summary: {exc}")
        return

    print(f"\n================ AI MATCHUP SUMMARY ({key_source}) ================")
    try:
        content = res.json()["choices"][0]["message"]["content"].strip()
        slow_print(content)
    except Exception as e:
        print("❌ Error generating Groq summary:", e)
        print(res.text)

def build_feature_row(team_a, team_b, team_data):
    flags_a = extract_archetype_flags(team_data[team_a])
    flags_b = extract_archetype_flags(team_data[team_b])
    row = build_model_feature_row(team_a, team_b, team_data)
    return pd.DataFrame([row]), flags_a, flags_b

def simulate_matchup(team_a, team_b):
    team_data = inject_all_teams()
    if team_a not in team_data or team_b not in team_data:
        print("❌ One or both teams not found.")
        return

    model = joblib.load(MODEL_PATH)
    feature_row, flags_a, flags_b = build_feature_row(team_a, team_b, team_data)
    X_model = feature_row.drop(columns=["team_a", "team_b"])

    prediction = model.predict(X_model)[0]
    proba = bound_probability(model.predict_proba(X_model)[0][prediction])
    predicted_team = team_a if prediction == 1 else team_b

    print(f"\n=== ML MATCHUP SIMULATION ===")
    print(f"{team_a.upper()} vs {team_b.upper()}")
    print(f"Predicted Winner: {predicted_team.upper()}")
    print(f"Confidence: {format_probability(proba)}\n")

    features = X_model.iloc[0]
    rush_edge = rating_edge_prob(features["a_run_game_vs_b_front"], scale=60)
    pass_edge = rating_edge_prob(features["a_pass_off_vs_b_pass_def"], scale=35)
    coverage_gap = rating_edge_prob(features["a_wr_vs_b_cb"], scale=45)

    print("🔍 UNIT MATCHUP ESTIMATES")
    print(f"{team_a.upper()} Rush Edge → {int(rush_edge * 100)}% vs {team_b.upper()} Front")
    print(f"{team_a.upper()} Pass Threat → {int(pass_edge * 100)}% vs {team_b.upper()} Coverage")
    print(f"{team_a.upper()} WR Separation → {int(coverage_gap * 100)}% vs {team_b.upper()} DBs\n")

    print("⚠️ CONDITIONAL SCENARIOS")
    insights = conditional_insights(flags_a, flags_b, team_a, team_b, features)
    for insight in insights:
        print("-", insight)

    analyst_context = build_matchup_context(team_a, team_b, team_data, features)
    send_groq_summary(team_a, team_b, predicted_team, proba, rush_edge, pass_edge, coverage_gap, insights, analyst_context)


if __name__ == "__main__":
    a = input("Enter first team name: ").strip().lower()
    b = input("Enter second team name: ").strip().lower()
    simulate_matchup(a, b)

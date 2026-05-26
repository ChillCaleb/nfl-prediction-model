import sqlite3
import pandas as pd
import time
import os
import sys
import importlib.util

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from groq_utils import get_groq_api_keys, get_groq_model, post_groq_chat_completion

spec = importlib.util.spec_from_file_location("archetype_rules", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Legacy_Files", "Engine", "archetype_rules.py")))
archetype_rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archetype_rules)
get_archetype = archetype_rules.get_archetype

PLAYER_DB = "Database/nfl_player_data.db"
RATING_DB = "Database/nfl_ratings.db"

GROQ_MODEL = get_groq_model()


def generate_llm_blurb(player_name, archetype, stats, ratings):
    if not get_groq_api_keys():
        return "[Scouting blurb could not be generated because no Groq API key is set.]"

    stat_lines = "\n".join([f"{k}: {v}" for k, v in stats.items()])
    rating_lines = "\n".join([f"{k}: {v}" for k, v in ratings.items()])

    prompt = f"""
Write a professional NFL scouting report for {player_name}, blending data with insight.
Do not mention any numerical ratings directly. Instead, guide your tone and focus based on context.

Use the following principles:
- If a player's raw rating is below 50, keep it short and minimal.
- If raw rating is between 50–79, use a balanced tone.
- If raw rating is 80+, highlight strengths energetically and back it up with stats.
- Only highlight passing, rushing, or scoring traits if their rating is above 20.
- Use the full name of any stat mentioned (e.g., "Yards After Catch" instead of "YAC").

Player Archetype: {archetype}

Ratings:
{rating_lines}

Stats:
{stat_lines}

Write in paragraph format with no emojis or section headers.
"""

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response, _ = post_groq_chat_completion(payload)
    except RuntimeError as e:
        print("\n❌ API error:", e)
        return "[Scouting blurb could not be generated due to API error.]"

    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("\n❌ API error:", response.status_code, response.text)
        return "[Scouting blurb could not be generated due to API error.]"


def get_player_blurb(player_name):
    player_lower = player_name.lower()
    conn1 = sqlite3.connect(PLAYER_DB)
    conn2 = sqlite3.connect(RATING_DB)

    def_df = pd.read_sql_query("SELECT * FROM defense", conn1)
    adv_def_df = pd.read_sql_query("SELECT * FROM advanced_defense", conn1)
    snap_df = pd.read_sql_query("SELECT * FROM snap_counts", conn1)
    pass_df = pd.read_sql_query("SELECT * FROM passing", conn1)
    adv_pass_df = pd.read_sql_query("SELECT * FROM advanced_passing", conn1)
    rushrecv_df = pd.read_sql_query("SELECT * FROM rushing_and_receiving", conn1)
    adv_rush_df = pd.read_sql_query("SELECT * FROM advanced_rushing", conn1)
    adv_recv_df = pd.read_sql_query("SELECT * FROM advanced_receiving", conn1)
    def_rating_df = pd.read_sql_query("SELECT * FROM Defensive_player_ratings", conn2)
    off_rating_df = pd.read_sql_query("SELECT * FROM Offensive_player_ratings", conn2)

    conn1.close()
    conn2.close()

    pos = None
    base_row = None

    # Determine position
    all_data = pd.concat([def_df, pass_df, rushrecv_df], axis=0)
    pos_row = all_data[all_data['Player'].str.lower() == player_lower]
    if pos_row.empty:
        return None
    pos = pos_row.iloc[0]['Pos']
    pos_upper = pos.upper()

    if pos_upper == "QB":
        base_row = pass_df[pass_df['Player'].str.lower() == player_lower]
        adv_info = adv_pass_df[adv_pass_df['Player'].str.lower() == player_lower]
    elif pos_upper == "RB":
        base_row = rushrecv_df[rushrecv_df['Player'].str.lower() == player_lower]
        adv_info = adv_rush_df[adv_rush_df['Player'].str.lower() == player_lower]
    elif pos_upper in ["WR", "TE"]:
        base_row = rushrecv_df[rushrecv_df['Player'].str.lower() == player_lower]
        adv_info = adv_recv_df[adv_recv_df['Player'].str.lower() == player_lower]
    else:
        base_row = def_df[def_df['Player'].str.lower() == player_lower]
        adv_info = adv_def_df[adv_def_df['Player'].str.lower() == player_lower]

    if base_row.empty:
        return None

    row = base_row.iloc[0]
    team = row['Team']
    snap_info = snap_df[snap_df['Player'].str.lower() == player_lower]

    is_offensive = pos_upper in ["QB", "RB", "WR", "TE", "OL"]
    rate_df = off_rating_df if is_offensive else def_rating_df
    rate_info = rate_df[rate_df['player'].str.lower() == player_lower]

    arch_info = get_archetype(pos, row, adv_info, snap_info)
    archetype = arch_info['archetype']
    reason = arch_info['reason']

    stats = row.to_dict()
    if not adv_info.empty:
        stats.update(adv_info.iloc[0].to_dict())
    if not snap_info.empty:
        stats['Snap%'] = snap_info.iloc[0].get('Def_Pct') or snap_info.iloc[0].get('Off_Pct') or '0%'
    stats['Archetype Reason'] = reason

    ratings = rate_info.iloc[0].to_dict() if not rate_info.empty else {}
    blurb = generate_llm_blurb(player_name, archetype, stats, ratings)

    return {
        "Player": player_name,
        "Position": pos,
        "Archetype": archetype,
        "Rating": ratings.get("raw", 0.0),
        "Blurb": blurb,
        "Stats": stats
    }


def slow_print(text, delay=0.04):
    for word in text.split():
        print(word, end=' ', flush=True)
        time.sleep(delay)
    print()


def analyze_player(player_name: str):
    result = get_player_blurb(player_name)
    if result is None:
        print(f"No data found for {player_name}")
        return

    print(f"\n===== Scouting Report: {player_name} =====\n")
    print(f"Position: {result['Position']}\nArchetype: {result['Archetype']}")

    # Print key stats before LLM blurb
    print("\n-- Key Stats --")
    for k, v in result["Stats"].items():
        if isinstance(v, (int, float)) and abs(v) > 0:
            print(f"{k}: {v}")
    print(f"\n===== Summary for: {player_name} =====\n")
    slow_print(result["Blurb"])


if __name__ == "__main__":
    name = input("Enter a player name: ")
    analyze_player(name.strip())

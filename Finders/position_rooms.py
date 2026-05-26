import os
import sys
import sqlite3
import pandas as pd
import time
import warnings

# Suppress pandas FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Use player-level blurb generator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from groq_utils import get_groq_api_keys, get_groq_model, post_groq_chat_completion
from Finders.player_breakdown import get_player_blurb  

GROQ_MODEL = get_groq_model()

PLAYER_DB = "Database/nfl_player_data.db"
RATING_DB = "Database/nfl_ratings.db"

def generate_room_blurb(position, team, player_blurbs, team_stats):
    if not get_groq_api_keys():
        return "[Room breakdown could not be generated because no Groq API key is set.]"

    summary = "\n".join([f"{k}: {v}" for k, v in team_stats.items() if isinstance(v, (int, float))])
    player_descriptions = "\n\n".join([f"{pb['Blurb']}" for pb in player_blurbs])

    prompt = f"""
Write a detailed positional room breakdown for the {team} {position} unit.

Context:
Team Performance:
{summary}

Player Scouting Summaries:
{player_descriptions}

Guidelines:
- Focus on how these players complement or contrast one another.
- Identify which archetypes or skill sets stand out or overlap.
- Use team trends and group dynamics to frame strengths/weaknesses.
- If multiple players share a style, comment on redundancy or synergy.
- Avoid repeating stat lines; synthesize the information.
- Do not use rating numbers or repeat the player names unnecessarily.
- No emojis, no bullet points.
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
        return "[Room breakdown could not be generated due to API error.]"

    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("\n❌ API error:", response.status_code, response.text)
        return "[Room breakdown could not be generated due to API error.]"

def slow_print(text, delay=0.04):
    for word in text.split():
        print(word, end=' ', flush=True)
        time.sleep(delay)
    print()

def analyze_positional_room(team: str, position: str):
    conn1 = sqlite3.connect(PLAYER_DB)
    conn2 = sqlite3.connect(RATING_DB)

    def_df = pd.read_sql_query("SELECT * FROM defense WHERE Team = ?", conn1, params=[team])
    pass_df = pd.read_sql_query("SELECT * FROM passing WHERE Team = ?", conn1, params=[team])
    rushrecv_df = pd.read_sql_query("SELECT * FROM rushing_and_receiving WHERE Team = ?", conn1, params=[team])
    team_rating = pd.read_sql_query("SELECT * FROM Defensive_team_ratings", conn2)

    conn1.close()
    conn2.close()

    pos_aliases = {
        "WR": ["WR", "W"],
        "CB": ["CB", "C", "DB", "LCB", "RCB"],
        "DL": ["DL", "DE", "DT", "EDGE", "NT", "LE", "RE", "LDE", "RDE", "D"],
        "QB": ["QB"],
        "RB": ["RB", "R"],
        "TE": ["TE"],
        "LB": ["LB", "MLB", "ILB", "OLB", "WLB", "SLB", "LOLB", "ROLB"],
        "S": ["S", "SS", "FS"],
        "OL": ["OL", "LT", "RT", "G", "LG", "RG", "C"]
    }
    aliases = pos_aliases.get(position.upper(), [position.upper()])

    if position in ["QB", "RB", "WR", "TE", "OL"]:
        pos_df = pass_df if position == "QB" else rushrecv_df
    else:
        pos_df = def_df

    filtered = pos_df[pos_df["Pos"].astype(str).str.upper().isin(aliases)]
    if filtered.empty:
        print("No positional players found for", team, position)
        return

    room = []

    for _, row in filtered.iterrows():
        name = row["Player"]
        blurb_info = get_player_blurb(name)
        if blurb_info:
            room.append(blurb_info)

    room.sort(key=lambda x: x["Rating"], reverse=True)

    team_row = team_rating[team_rating["team"].str.lower() == team.lower()]
    team_stats = team_row.iloc[0].to_dict() if not team_row.empty else {}

    print(f"\n===== {team.upper()} {position.upper()} Room Breakdown =====\n")
    print("Players in Room:", ", ".join([r["Player"] for r in room]))
    print()
    slow_print(generate_room_blurb(position, team, room, team_stats))

if __name__ == "__main__":
    t = input("Enter team (e.g. ravens): ").strip().lower()
    p = input("Enter position group (e.g. CB, S, DL, LB): ").strip().upper()
    analyze_positional_room(t, p)

import sqlite3
import io
import sys
from contextlib import redirect_stdout
import requests
import os
import time

from Finders.position_rooms import analyze_positional_room
from Finders.team_breakdowns import run_team_breakdown

# Custom matchup probability functions (logistic-style)
def unit_advantage_prob(offense_rating, defense_rating, scale=15):
    delta = offense_rating - defense_rating
    return 1 / (1 + 10 ** (-delta / scale))

def matchup_win_probability(team1_total, team2_total, scale=20):
    return 1 / (1 + 10 ** ((team2_total - team1_total) / scale))

def slow_print(text, delay=0.04):
    for word in text.split():
        print(word, end=' ', flush=True)
        time.sleep(delay)
    print()

def get_team_rating_from_db(team_name, rating_db_path="Database/nfl_ratings.db"):
    conn = sqlite3.connect(rating_db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM Offensive_team_ratings WHERE team = ? COLLATE NOCASE", (team_name,))
    off_row = cur.fetchone()
    cur.execute("SELECT * FROM Defensive_team_ratings WHERE team = ? COLLATE NOCASE", (team_name,))
    def_row = cur.fetchone()

    if not off_row or not def_row:
        raise ValueError(f"Team '{team_name}' not found in ratings database.")

    off_cols = [desc[0] for desc in cur.description]
    cur.execute("PRAGMA table_info(Defensive_team_ratings)")
    def_cols = [col[1] for col in cur.fetchall()]

    conn.close()

    off_dict = dict(zip(off_cols, off_row))
    def_dict = dict(zip(def_cols, def_row))

    profile = {
        "team": team_name,
        "overall": off_dict.get("total", 0) + def_dict.get("total", 0),
        "rush_rating": off_dict.get("rushing", 0),
        "pass_rating": off_dict.get("passing", 0),
        "score_rating": off_dict.get("scoring", 0),
        "offensive_line": off_dict.get("ol", 0),
        "run_defense": def_dict.get("rushing", 0),
        "pass_defense": def_dict.get("passing", 0),
        "def_score": def_dict.get("scoring", 0),
        "defensive_line": def_dict.get("dl", 0),
    }
    return profile


def extract_most_prominent_room(text):
    for line in text.splitlines():
        if "MOST PROMINENT POSITIONAL ROOM" in line:
            return line.split(":")[-1].strip().upper()
    return None

def extract_top_contributor(text):
    for line in text.splitlines():
        if "Raw Rating" in line:
            return line.split("(")[0].strip()
    return None

def generate_matchup_blurb(summary_text, team1, team2):
    prompt = f"""
You are a professional NFL analyst. Write a matchup preview between the {team1} and {team2} using the summary below. Focus on how each team's strengths — including positional groups and key players — will influence the game.

Avoid listing stats directly. Be concise, insightful, and matchup-specific. Highlight key battles (e.g., trenches, coverage mismatches, QB pressure).

---
{summary_text}
"""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("GROQ API key not found.")
        return

    res = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}"},
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
    )
    print("\n================ AI MATCHUP SUMMARY ================")
    try:
        slow_print(res.json()["choices"][0]["message"]["content"].strip())
    except Exception as e:
        print("❌ Error generating Groq summary:", e)
        print(res.text)


def compare_matchup(team1_name, team2_name):
    team1 = get_team_rating_from_db(team1_name)
    team2 = get_team_rating_from_db(team2_name)

    header = f"====================== MATCHUP PREDICTION ======================"
    subhead = f"{team1_name.upper()} vs {team2_name.upper()}\n"
    summary = []

    win_prob = matchup_win_probability(team1['overall'], team2['overall'])
    winner = team1_name if win_prob > 0.5 else team2_name
    summary.append(f"🏆 Predicted Winner: {winner.upper()}")
    summary.append(f"📊 Win Probability: {team1_name} {round(win_prob*100)}% | {team2_name} {round((1-win_prob)*100)}%\n")

    rush_1v2 = unit_advantage_prob(team1['rush_rating'], team2['run_defense'])
    pass_1v2 = unit_advantage_prob(team1['pass_rating'], team2['pass_defense'])
    score_1v2 = unit_advantage_prob(team1['score_rating'], team2['def_score'])

    rush_2v1 = unit_advantage_prob(team2['rush_rating'], team1['run_defense'])
    pass_2v1 = unit_advantage_prob(team2['pass_rating'], team1['pass_defense'])
    score_2v1 = unit_advantage_prob(team2['score_rating'], team1['def_score'])

    summary.append("------ UNIT MATCHUP BREAKDOWNS ------")
    summary.append(f"{team1_name} RUSH OFF vs {team2_name} RUSH DEF → {round(rush_1v2 * 100)}% advantage")
    summary.append(f"{team1_name} PASS OFF vs {team2_name} PASS DEF → {round(pass_1v2 * 100)}% advantage")
    summary.append(f"{team1_name} SCORING vs {team2_name} SCORE DEF → {round(score_1v2 * 100)}% advantage\n")
    summary.append(f"{team2_name} RUSH OFF vs {team1_name} RUSH DEF → {round(rush_2v1 * 100)}% advantage")
    summary.append(f"{team2_name} PASS OFF vs {team1_name} PASS DEF → {round(pass_2v1 * 100)}% advantage")
    summary.append(f"{team2_name} SCORING vs {team1_name} SCORE DEF → {round(score_2v1 * 100)}% advantage\n")

    summary_block = "\n".join(summary)
    full = header + "\n" + subhead + "\n" + summary_block + "\n==============================================================="
    slow_print(full)

    def capture_team_context(team):
        buf = io.StringIO()
        with redirect_stdout(buf):
            run_team_breakdown(team)
        out = buf.getvalue()
        room = extract_most_prominent_room(out)
        player = extract_top_contributor(out)
        print(out)
        return room, player

    room1, player1 = capture_team_context(team1_name)
    room2, player2 = capture_team_context(team2_name)

    if room1:
        print(f"\n================ {team1_name.upper()} POSITIONAL ROOM: {room1} ================")
        analyze_positional_room(team1_name, room1)
    if room2:
        print(f"\n================ {team2_name.upper()} POSITIONAL ROOM: {room2} ================")
        analyze_positional_room(team2_name, room2)

    matchup_summary_text = f"""
Matchup: {team1_name} vs {team2_name}
Predicted Winner: {winner} ({round(win_prob*100)}%)

🔹 Matchup Edges:
{team1_name} RUSH OFF vs {team2_name} RUSH DEF → {round(rush_1v2 * 100)}%
{team1_name} PASS OFF vs {team2_name} PASS DEF → {round(pass_1v2 * 100)}%
{team1_name} SCORING vs {team2_name} SCORE DEF → {round(score_1v2 * 100)}%

{team2_name} RUSH OFF vs {team1_name} RUSH DEF → {round(rush_2v1 * 100)}%
{team2_name} PASS OFF vs {team1_name} PASS DEF → {round(pass_2v1 * 100)}%
{team2_name} SCORING vs {team1_name} SCORE DEF → {round(score_2v1 * 100)}%

🔹 Positional Rooms:
{team1_name} Room: {room1} | Top Player: {player1}
{team2_name} Room: {room2} | Top Player: {player2}

🔹 Conditional Trends:
- If {team1_name} fails to establish the run or pass, offensive collapse is likely.
- If {team1_name} starts hot through the air, expect red zone dominance.
- If {team2_name}'s defensive line outmatches {team1_name}'s OL, pocket collapse may be frequent.
"""

    generate_matchup_blurb(matchup_summary_text, team1_name, team2_name)
    return full


if __name__ == "__main__":
    team1 = input("Enter Team 1: ").strip()
    team2 = input("Enter Team 2: ").strip()
    compare_matchup(team1, team2)
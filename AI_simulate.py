import joblib
import pandas as pd
from player_injection import inject_all_teams
from train_rf_data import extract_archetype_flags
import os
import requests
import time
from dotenv import load_dotenv
from dotenv import load_dotenv
from pathlib import Path

# === Load Environment ===
load_dotenv(dotenv_path=Path("Finders/.env"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# === Load Environment ===
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_PATH = "Model/rf_matchup_model.joblib"

def unit_advantage_prob(team_flag, opp_flag, weight=0.5):
    return 0.55 if team_flag and not opp_flag else 0.5 if team_flag and opp_flag else 0.45 if not team_flag and opp_flag else 0.5

def conditional_insights(flags_a, flags_b, team_a, team_b):
    insights = []
    if flags_a["has_dual_threat_qb"] and not flags_b["has_star_rusher"]:
        insights.append(f"If {team_a.upper()} QB escapes the pocket, {team_b.upper()} may struggle to contain.")
    if flags_b["has_elite_receiver"] and not flags_a["has_lockdown_cb"]:
        insights.append(f"{team_b.upper()} receivers may dominate in space with no elite CBs on {team_a.upper()}.")
    if flags_a["has_star_rusher"] and flags_b["has_dual_threat_qb"]:
        insights.append(f"Expect trench warfare: {team_a.upper()} front vs {team_b.upper()} mobile QB.")
    if flags_b["team_elite_archetype_count"] < 2:
        insights.append(f"If {team_a.upper()} starts hot, {team_b.upper()} lacks enough elite players to counter.")
    return insights

def slow_print(text, delay=0.04):
    for word in text.split():
        print(word, end=' ', flush=True)
        time.sleep(delay)
    print()

def send_groq_summary(team_a, team_b, predicted_team, proba, rush, passthrow, sep, insights):
    if not GROQ_API_KEY:
        print("❌ GROQ_API_KEY not found in environment. Please add it to your .env file.")
        return

    insights_block = "\n".join(["- " + i for i in insights])
    prompt = f"""
Matchup: {team_a} vs {team_b}
ML Prediction: {predicted_team} (confidence {proba:.2%})

Unit Probabilities:
- Rush Success: {int(rush * 100)}%
- Pass Success: {int(passthrow * 100)}%
- WR Separation: {int(sep * 100)}%

Conditional What-Ifs:
{insights_block}

Write a short, matchup-specific preview using this information. Be insightful and concise.
"""

    res = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
        }
    )
    print("\n================ AI MATCHUP SUMMARY ================")
    try:
        content = res.json()["choices"][0]["message"]["content"].strip()
        slow_print(content)
    except Exception as e:
        print("❌ Error generating Groq summary:", e)
        print(res.text)

def build_feature_row(team_a, team_b, team_data):
    flags_a = extract_archetype_flags(team_data[team_a])
    flags_b = extract_archetype_flags(team_data[team_b])

    row = {
        "team_a": team_a,
        "team_b": team_b,
    }
    for key in flags_a:
        row[f"a_{key}"] = flags_a[key]
    for key in flags_b:
        row[f"b_{key}"] = flags_b[key]

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
    proba = model.predict_proba(X_model)[0][prediction]
    predicted_team = team_a if prediction == 1 else team_b

    print(f"\n=== ML MATCHUP SIMULATION ===")
    print(f"{team_a.upper()} vs {team_b.upper()}")
    print(f"Predicted Winner: {predicted_team.upper()}")
    print(f"Confidence: {proba:.2%}\n")

    # Unit advantage logic
    rush_edge = unit_advantage_prob(flags_a["has_star_rusher"], flags_b["has_star_rusher"])
    pass_edge = unit_advantage_prob(flags_a["has_elite_receiver"], flags_b["has_lockdown_cb"])
    coverage_gap = unit_advantage_prob(flags_a["has_route_runner"], flags_b["has_lockdown_cb"])

    print("🔍 UNIT MATCHUP ESTIMATES")
    print(f"{team_a.upper()} Rush Edge → {int(rush_edge * 100)}% vs {team_b.upper()} Front")
    print(f"{team_a.upper()} Pass Threat → {int(pass_edge * 100)}% vs {team_b.upper()} Coverage")
    print(f"{team_a.upper()} WR Separation → {int(coverage_gap * 100)}% vs {team_b.upper()} DBs\n")

    print("⚠️ CONDITIONAL SCENARIOS")
    insights = conditional_insights(flags_a, flags_b, team_a, team_b)
    for insight in insights:
        print("-", insight)

    send_groq_summary(team_a, team_b, predicted_team, proba, rush_edge, pass_edge, coverage_gap, insights)


if __name__ == "__main__":
    a = input("Enter first team name: ").strip().lower()
    b = input("Enter second team name: ").strip().lower()
    simulate_matchup(a, b)
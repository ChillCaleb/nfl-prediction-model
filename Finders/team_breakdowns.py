import sqlite3
import pandas as pd
import requests
import time

GROQ_API_KEY = "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"

# === Setup ===
player_db = sqlite3.connect("Database/nfl_player_data.db")
rating_db = sqlite3.connect("Database/nfl_ratings.db")

def slow_print(text, delay=0.04):
    for word in text.split():
        print(word, end=' ', flush=True)
        time.sleep(delay)
    print()

def generate_team_blurb(team_name, team_stats, top_offense, top_defense):
    off_stats = team_stats.get("off", {})
    def_stats = team_stats.get("def", {})
    off_players = "\n".join([f"- {row['player']} ({row['pos']}): {row['archetype']}" for _, row in top_offense.iterrows()])
    def_players = "\n".join([f"- {row['player']} ({row['pos']}): {row['archetype']}" for _, row in top_defense.iterrows()])

    summary = f"""
Write a full NFL team scouting report for the {team_name}.

Top Offensive Contributors:
{off_players}

Top Defensive Contributors:
{def_players}

Offensive Team Stats:
""" + "\n".join([f"{k}: {v}" for k, v in off_stats.items()]) + "\n\nDefensive Team Stats:\n" + "\n".join([f"{k}: {v}" for k, v in def_stats.items()]) + """

Do not mention any numerical values or positions directly. Use the archetypes and data to describe the team's overall tendencies, synergy, standout traits, and schematic identity. Write in complete paragraphs with a confident, analytical tone.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {"role": "user", "content": summary}
        ]
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("\n❌ API error:", response.status_code, response.text)
        return "[Team breakdown could not be generated due to API error.]"

def get_archetype(pos, base_row, adv_row, snap_row=None):
    def val(r, col):
        try: return float(r.get(col, 0)) if col in r else 0.0
        except: return 0.0

    pos = pos.upper()
    row = adv_row.iloc[0] if not adv_row.empty else {}
    pressures = val(row, "Prss"); targets = val(row, "Tgt"); completions = val(row, "Cmp")
    tfl = val(row, "TFL"); pd_def = val(row, "PD"); ints = val(row, "Int"); tackles = val(row, "Comb")
    completion_rate = (completions / targets) * 100 if targets > 0 else 0.0

    if any(x in pos for x in ["CB", "DB", "C"]):
        snap_count = val(row, "def_num") or val(base_row, "Def_Num") or float(snap_row.iloc[0].get("Def_Num", 0) if snap_row is not None and not snap_row.empty else 0)
        target_rate = (targets / snap_count) * 100 if snap_count else 100.0
        if snap_count >= 500 and target_rate < 10: return "Lockdown Corner"
        if targets >= 30 and completion_rate < 60: return "Coverage Corner"
        if ints >= 3 and pd_def >= 10 and tackles >= 60: return "Elite Balanced Corner"
        return "Balanced Corner"

    if pos in ["S", "FS", "SS"]:
        if pressures >= 5: return "Blitzer Safety"
        if targets >= 10 and completion_rate < 65: return "Coverage Safety"
        if pressures >= 3 and targets >= 10 and completion_rate < 70 and tfl >= 5: return "Elite Balanced Safety"
        return "Balanced Safety"

    if "LB" in pos or pos == "L":
        if pressures >= 10: return "Blitzing Linebacker"
        if targets >= 20 and completion_rate < 60: return "Coverage Linebacker"
        if pressures >= 6 and tfl >= 6 and targets >= 15 and completion_rate < 65: return "Elite Balanced Linebacker"
        return "Balanced Linebacker"

    if pos in ["DL", "DE", "DT", "EDGE", "LE", "RE", "D"]:
        if pressures >= 5 and tfl >= 3: return "Dual Threat Lineman"
        if pressures >= 5: return "Pass Rush Specialist"
        if tfl >= 3: return "Run Stopper"
        if pressures >= 3 and tfl >= 2: return "Elite Balanced Lineman"
        return "Balanced Lineman"

    if pos == "QB":
        td = val(base_row, "TD"); int_ = val(base_row, "Int"); yds = val(base_row, "Yds")
        comp = val(base_row, "Cmp"); att = val(base_row, "Att")
        cmp_pct = (comp / att) * 100 if att else 0.0
        if yds >= 4000 and cmp_pct >= 66 and td >= 30 and int_ <= 7: return "All-Around Elite QB"
        if cmp_pct >= 68 and td / (int_ or 1) >= 4: return "Efficient Passer"
        if yds >= 3000 and cmp_pct >= 64: return "Volume Distributor"
        return "Balanced QB"

    if pos == "RB":
        rush_yds = val(adv_row, "Yds")
        brk_tkl = val(adv_row, "BrkTkl")

        # Pull from rushing_and_receiving base_row
        ypc = val(base_row, "Rushing - Y/A")
        rec = val(base_row, "Receiving - Rec")
        rec_yds = val(base_row, "Receiving - Yds")

        is_receiving_back = rec >= 15 and rec_yds >= 250
        is_power_runner = rush_yds >= 800 and ypc >= 4.2

        if is_receiving_back and is_power_runner:
            return "All-Around Elite RB"
        if is_receiving_back:
            return "Receiving Back RB"
        if is_power_runner:
            return "Power Runner RB"
        return "Balanced RB"


    if pos == "TE":
        rec = val(row, "Rec"); yds = val(row, "Yds"); tgt = val(row, "Tgt")
        one_d = val(row, "1D"); yac_r = val(row, "YAC/R"); catch_pct = rec / tgt if tgt else 0
        if rec >= 60 and yds >= 800 and catch_pct >= 0.65 and yac_r >= 3 and one_d >= 40: return "All-Around Elite TE"
        if catch_pct >= 75 and yds / tgt >= 7: return "Possession TE"
        if yac_r >= 6.0: return "YAC Specialist"
        if one_d / rec >= 0.6: return "Red Zone Threat"
        return "Balanced TE"
    
    if pos == "WR":
        rec = val(adv_row, "Rec")
        yds = val(adv_row, "Yds")
        tgt = val(adv_row, "Tgt")
        adot = val(adv_row, "ADOT")
        yac = val(adv_row, "YAC")
        one_d = val(adv_row, "1D")
        drop = val(adv_row, "Drop")
        catch_pct = rec / tgt if tgt else 0

        # All-Around WR: Volume + efficiency + YAC + depth
        if rec >= 70 and yds >= 1000 and catch_pct >= 0.65 and yac / rec >= 3 and adot >= 8:
            return "All-Around Elite WR"

        # Possession Receiver: Reliable hands, low depth
        if catch_pct >= 0.75 and adot <= 9:
            return "Possession Receiver WR"

        # YAC specialist: Turns short throws into gains
        if rec and yac / rec >= 6.0:
            return "YAC Specialist WR"

        # Deep threat: High ADOT
        if adot >= 12:
            return "Deep Threat WR"

        return "Balanced WR"


    return "Unknown"

def run_team_breakdown(team):
    off_team = pd.read_sql_query("SELECT * FROM Offensive_team_ratings WHERE team = ?", rating_db, params=[team])
    def_team = pd.read_sql_query("SELECT * FROM Defensive_team_ratings WHERE team = ?", rating_db, params=[team])
    off_ratings = pd.read_sql_query("SELECT * FROM Offensive_player_ratings WHERE team = ?", rating_db, params=[team])
    def_ratings = pd.read_sql_query("SELECT * FROM Defensive_player_ratings WHERE team = ?", rating_db, params=[team])

    top_off = off_ratings[off_ratings["raw"] > 0].drop_duplicates("player").sort_values("raw", ascending=False).head(5)
    top_def = def_ratings[def_ratings["raw"] > 0].drop_duplicates("player").sort_values("raw", ascending=False).head(5)

    off_avg = off_ratings.groupby("pos")["raw"].mean()
    def_avg = def_ratings.groupby("pos")["raw"].mean()
    room_avg = pd.concat([off_avg, def_avg]).groupby(level=0).mean().sort_values(ascending=False)

    pass_base = pd.read_sql("SELECT * FROM passing", player_db)
    rush_base = pd.read_sql("SELECT * FROM rushing_and_receiving", player_db)
    def_base = pd.read_sql("SELECT * FROM defense", player_db)
    adv_pass = pd.read_sql("SELECT * FROM advanced_passing", player_db)
    adv_rush = pd.read_sql("SELECT * FROM advanced_rushing", player_db)
    adv_recv = pd.read_sql("SELECT * FROM advanced_receiving", player_db)
    adv_def = pd.read_sql("SELECT * FROM advanced_defense", player_db)
    snaps = pd.read_sql("SELECT * FROM snap_counts", player_db)

    sacks = off_team["sacks"].iloc[0] if "sacks" in off_team else 99
    rush_yds = off_team["rush_yds"].iloc[0] if "rush_yds" in off_team else 0
    if sacks < 25 and rush_yds > 2000: ol_type = "All-Around Elite OL"
    elif sacks < 25: ol_type = "Elite Pass Blocker"
    elif rush_yds > 2000: ol_type = "Elite Run Blocker"
    else: ol_type = "Balanced OL"

    def val(r, col): return float(r.get(col, 0)) if col in r and r.get(col) not in [None, ''] else 0.0

    def resolve(df):
        out = []
        for _, row in df.iterrows():
            p, pos = row["player"], row["pos"]
            if pos == "OL": out.append(ol_type); continue
            p_l = p.lower()
            if pos == "QB": base, adv = pass_base, adv_pass
            elif pos == "RB": base, adv = rush_base, adv_rush
            elif pos == "TE": base, adv = rush_base, adv_recv
            elif pos == "WR": base, adv = rush_base, adv_recv
            else: base, adv = def_base, adv_def
            b = base[base["Player"].str.lower() == p_l].iloc[0].to_dict() if not base[base["Player"].str.lower() == p_l].empty else {}
            a = adv[adv["Player"].str.lower() == p_l] if not adv.empty else pd.DataFrame()
            s = snaps[snaps["Player"].str.lower() == p_l]
            out.append(get_archetype(pos, b, a, s))
        return out

    top_off["archetype"] = resolve(top_off)
    top_def["archetype"] = resolve(top_def)

    print(f"\n===== {team.upper()} Team Breakdown =====\n")
    print("\n🏈 TEAM EFFICIENCY & PROFILE:")
    print("\n-- Offensive Team Ratings --")
    for col in ["rushing", "passing", "scoring", "total"]:
        if col in off_team.columns:
            print(f"{col}: {off_team[col].iloc[0]:.2f}")

    print("\n-- Defensive Team Ratings --")
    for col in ["rushing", "passing", "scoring", "total"]:
        if col in def_team.columns:
            print(f"{col}: {def_team[col].iloc[0]:.2f}")

    print("\n---\n\n🔥 TOP 5 OFFENSIVE CONTRIBUTORS:")
    for _, r in top_off.iterrows():
        print(f"{r['player']} ({r['pos']}) — {r['archetype']} — Raw Rating: {r['raw']:.2f}")

    print("\n---\n\n🛡️ TOP 5 DEFENSIVE CONTRIBUTORS:")
    for _, r in top_def.iterrows():
        print(f"{r['player']} ({r['pos']}) — {r['archetype']} — Raw Rating: {r['raw']:.2f}")

    print("\n---\n\n📈 POSITIONAL UNIT RATINGS:")
    for _, row in room_avg.reset_index().iterrows():
        print(f"{row['pos']}: {row['raw']:.2f}")

    print("\n---\n\n🧩 MOST PROMINENT POSITIONAL ROOM:")
    room_counts = top_def['pos'].value_counts().add(top_off['pos'].value_counts(), fill_value=0)
    print(room_counts.idxmax())

    team_stats = {
        "off": off_team.iloc[0].to_dict(),
        "def": def_team.iloc[0].to_dict()
    }
    return team, team_stats, top_off, top_def

if __name__ == "__main__":
    user_input = input("Enter team (e.g. ravens, 49ers, chiefs): ").strip().lower()
    team, team_stats, top_off, top_def = run_team_breakdown(user_input)
    print("\n===== TEAM NARRATIVE (Groq) =====\n")
    slow_print(generate_team_blurb(team, team_stats, top_off, top_def))

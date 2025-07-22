import sqlite3
import pandas as pd

DB_PATH = "Database/nfl_ratings.db"
PLAYER_DB = "Database/nfl_player_data.db"


def load_ratings():
    conn = sqlite3.connect(DB_PATH)
    off = pd.read_sql("SELECT player, team, pos, raw, archetype FROM Offensive_player_ratings", conn)
    def_ = pd.read_sql("SELECT player, team, pos, raw, archetype FROM Defensive_player_ratings", conn)
    conn.close()
    return off, def_


def load_all_stats():
    conn = sqlite3.connect(PLAYER_DB)
    defense = pd.read_sql("SELECT * FROM defense", conn)
    advanced_def = pd.read_sql("SELECT * FROM advanced_defense", conn)
    offense = pd.read_sql("SELECT * FROM rushing_and_receiving", conn)
    advanced_rush = pd.read_sql("SELECT * FROM advanced_rushing", conn)
    advanced_recv = pd.read_sql("SELECT * FROM advanced_receiving", conn)
    passing = pd.read_sql("SELECT * FROM passing", conn)
    advanced_pass = pd.read_sql("SELECT * FROM advanced_passing", conn)
    snap_counts = pd.read_sql("SELECT * FROM snap_counts", conn)
    conn.close()
    return {
        "def": defense,
        "adv_def": advanced_def,
        "off": offense,
        "adv_rush": advanced_rush,
        "adv_recv": advanced_recv,
        "pass": passing,
        "adv_pass": advanced_pass,
        "snaps": snap_counts
    }


def build_team_vector(team_name, off_df, def_df, stats):
    team_off = off_df[off_df["team"].str.lower() == team_name.lower()]
    team_def = def_df[def_df["team"].str.lower() == team_name.lower()]
    full_roster = pd.concat([team_off, team_def])

    players = []

    for _, row in full_roster.iterrows():
        player_name = row["player"].strip()
        pos = row["pos"].strip()
        archetype = row["archetype"].strip()
        raw = row["raw"]

        label = f"{player_name} ({pos}, {archetype})"
        players.append({
            "name": player_name,
            "position": pos,
            "archetype": archetype,
            "raw": raw,
            "label": label
        })

    return players


def inject_all_teams():
    off_df, def_df = load_ratings()
    stats = load_all_stats()
    all_teams = off_df["team"].unique().tolist() + def_df["team"].unique().tolist()
    all_teams = sorted(list(set([t.lower() for t in all_teams])))

    output = {}
    for team in all_teams:
        output[team] = build_team_vector(team, off_df, def_df, stats)

    return output


if __name__ == "__main__":
    teams = inject_all_teams()
    for team, roster in teams.items():
        print(f"\n=== {team.upper()} ===")
        for player in roster:
            print(player["label"])

import pandas as pd
from data_loader import get_schedule_df  # Load the full NFL schedule from CSV

# Static 2023 team ratings used to calculate opponent strength
ratings_2023 = {
    'San Francisco 49ers': 100.0,
    'Dallas Cowboys': 88.65,
    'Detroit Lions': 67.25,
    'Los Angeles Rams': 61.57,
    'New Orleans Saints': 58.08,
    'Green Bay Packers': 53.71,
    'Tampa Bay Buccaneers': 53.28,
    'Philadelphia Eagles': 48.03,
    'Minnesota Vikings': 45.85,
    'Seattle Seahawks': 44.10,
    'Chicago Bears': 39.74,
    'Atlanta Falcons': 26.64,
    'Arizona Cardinals': 24.89,
    'New York Giants': 13.97,
    'Carolina Panthers': 5.24,
    'Washington Commanders': 0.0,
    'Baltimore Ravens': 100.0,
    'Buffalo Bills': 68.25,
    'Miami Dolphins': 58.29,
    'Kansas City Chiefs': 54.98,
    'Cleveland Browns': 53.08,
    'Cincinnati Bengals': 45.50,
    'Jacksonville Jaguars': 44.08,
    'Pittsburgh Steelers': 40.76,
    'Houston Texans': 39.34,
    'Las Vegas Raiders': 33.18,
    'Indianapolis Colts': 31.28,
    'Los Angeles Chargers': 27.01,
    'Tennessee Titans': 22.27,
    'Denver Broncos': 19.43,
    'New York Jets': 9.95,
    'New England Patriots': 0.0
}

# Modifier to adjust a base rating according to opponent difficulty
def apply_sos_modifier(base_rating, team_abbr, sos_dict, league_avg):
    team_sos = sos_dict.get(team_abbr, league_avg)  # Get the team's schedule difficulty
    modifier = team_sos / league_avg  # Calculate how it compares to average
    return base_rating * modifier  # Scale the rating accordingly

# Core SoS function that calculates average opponent strength per team
def calculate_strength_of_schedule(schedule_df, ratings_2023):
    print("📥 Cleaning and preparing schedule data...")
    schedule_df = schedule_df.dropna(subset=["Winner/tie", "Loser/tie"])  # Remove games with missing teams
    teams = pd.unique(schedule_df[["Winner/tie", "Loser/tie"]].values.ravel())  # All unique team names
    sos = {}  # Dictionary to store calculated SoS

    print("🔎 Computing opponent ratings for each team...")
    for team in teams:
        opps_w = schedule_df[schedule_df["Winner/tie"] == team]["Loser/tie"].tolist()  # Opponents in wins
        opps_l = schedule_df[schedule_df["Loser/tie"] == team]["Winner/tie"].tolist()  # Opponents in losses
        opponents = opps_w + opps_l  # All opponents

        valid_opps = [ratings_2023[opp] for opp in opponents if opp in ratings_2023]  # Only rated opponents
        sos[team] = sum(valid_opps) / len(valid_opps) if valid_opps else 0.0  # Avg opponent strength

    return sos

# Top-level access point for SoS and league average
def get_sos_info():
    print("📄 Loading NFL schedule CSV...")
    schedule_df = get_schedule_df()  # Load from data_loader

    print("🧠 Calculating Strength of Schedule...")
    sos_dict = calculate_strength_of_schedule(schedule_df, ratings_2023)

    print("📊 Computing league-wide average SoS...")
    league_avg = sum(sos_dict.values()) / len(sos_dict)  # Mean SoS value

    return sos_dict, league_avg

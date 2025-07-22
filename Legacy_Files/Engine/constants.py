# constants.py

column_mappings = {
    "Points_For": ["Points_For", "Points", "Pts", "PA"],
    "Total_Yards": ["Total_Yards", "Yds", "Yards"],
    "Yards_Per_Play": ["Yards_Per_Play", "Y/P", "YPP"],
    "Third_Down_Efficiency": ["3D%", "Third_Down%", "3rd Down %"],
    "Fourth_Down_Efficiency": ["4D%", "Fourth_Down%", "4th Down %"],
    "Red_Zone_Efficiency": ["RZPct", "Red Zone %"],
    "Drive_Score_Pct": ["Sc%", "Drive Scoring %"],
    "Drive_Turnover_Pct": ["TO%", "Takeaway%", "Drive Turnovers"],
    "Turnovers": ["TO%", "Turnovers", "TOs", "T/O", "Takeaways"],
    "Yards_Per_Drive": ["Yds/Drive"],
    "Points_Per_Drive": ["Pts/Drive"],
    "Sacks": ["Sacks", "Sk"],
    "Sack_Percentage": ["Sk%", "Sack%"],
    "Explosives": ["EXP", "Explosive", "Big Plays"],
    "Penalties": ["Penalties", "Pen"],
    "INT": ["INT", "Interceptions"],
    "First_Downs": ["1stD", "First Downs"],
    "FG%": ["FG%", "FieldGoal%", "Field Goal %"],
    "XP%": ["XP%", "ExtraPoint%", "Extra Point %"],
    "Punt_AVG": ["Punt_AVG", "Punting Avg", "Punt Average"],
    "KR_AVG": ["KR_AVG", "Kick Return Avg"],
    "PR_AVG": ["PR_AVG", "Punt Return Avg"],
    "home": ["Home", "home", "Hm", "hm"],
    "away": ["Away", "away", "Aw", "aw"],
    "team_points": ["Team_Points", "Points_For", "Score", "Pts"],
    "opponent": ["Opponent", "opp", "Opp", "Versus"]
}


# Abbreviations → Full team name mapping
abbr_to_full = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB":  "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC":  "Kansas City Chiefs",
    "LV":  "Las Vegas Raiders",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE":  "New England Patriots",
    "NO":  "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF":  "San Francisco 49ers",
    "TB":  "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders"
}

team_name_alias = {
    "ARI": "cardinals",
    "ATL": "falcons",
    "BAL": "ravens",
    "BUF": "bills",
    "CAR": "panthers",
    "CHI": "bears",
    "CIN": "bengals",
    "CLE": "browns",
    "DAL": "cowboys",
    "DEN": "broncos",
    "DET": "lions",
    "GB": "packers",
    "HOU": "texans",
    "IND": "colts",
    "JAX": "jaguars",
    "KC": "chiefs",
    "LV": "raiders",
    "LAC": "chargers",
    "LAR": "rams",
    "MIA": "dolphins",
    "MIN": "vikings",
    "NE": "patriots",
    "NO": "saints",
    "NYG": "giants",
    "NYJ": "jets",
    "PHI": "eagles",
    "PIT": "steelers",
    "SEA": "seahawks",
    "SF": "49ers",
    "TB": "buccaneers",
    "TEN": "titans",
    "WAS": "commanders"
}


# Full team name → Abbreviations
full_to_abbr = {v: k for k, v in abbr_to_full.items()}

team_name_map = {
    abbr: full.lower()
    for abbr, full in abbr_to_full.items()
}

snap_name_map = {
    abbr: abbr_to_full[abbr]
    for abbr in abbr_to_full
}



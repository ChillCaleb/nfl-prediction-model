import pandas as pd
from pathlib import Path

# Load the master list of restored players
restored_df = pd.read_csv("restored_players_master.csv")

# Folder where your cleaned CSVs are stored
base_path = Path("NFL")
defense_paths = list(base_path.rglob("defense.csv"))

# Append each player to their team's CSV
for team in restored_df["Team"].unique():
    team_df = restored_df[restored_df["Team"] == team].drop(columns="Team")
    match_file = next((f for f in defense_paths if team.lower() in str(f).lower()), None)

    if match_file:
        df = pd.read_csv(match_file)
        team_df.columns = df.columns  # align columns
        updated = pd.concat([df, team_df], ignore_index=True)
        updated.to_csv(match_file, index=False)
        print(f"[✓] Appended {len(team_df)} players to {match_file}")
    else:
        print(f"[!] No match found for team: {team}")

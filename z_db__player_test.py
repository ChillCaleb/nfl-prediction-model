import sqlite3
import pandas as pd

# --- CONFIG ---
db_path = "Database/nfl_player_data.db"
player_name = "Kenny Clark"  # Can be changed
team = "Packers"             # Input is mixed-case

# --- CONNECT ---
conn = sqlite3.connect(db_path)

# --- SQL QUERIES (Normalized Team Case) ---
team_lower = team.lower()
def_query = f"SELECT * FROM defense WHERE LOWER(Team) = '{team_lower}'"
adv_def_query = f"SELECT * FROM advanced_defense WHERE LOWER(Team) = '{team_lower}'"
snap_query = f"SELECT * FROM snap_counts WHERE LOWER(Team) = '{team_lower}'"

def_df = pd.read_sql_query(def_query, conn)
adv_def_df = pd.read_sql_query(adv_def_query, conn)
snap_df = pd.read_sql_query(snap_query, conn)

conn.close()

# --- FILTER BY PLAYER ---
def_filtered = def_df[def_df['Player'].str.contains(player_name, case=False, na=False)]
adv_def_filtered = adv_def_df[adv_def_df['Player'].str.contains(player_name, case=False, na=False)]
snap_filtered = snap_df[snap_df['Player'].str.contains(player_name, case=False, na=False)]

# --- DISPLAY DEFENSE STATS ---
print("\n--- DEFENSE STATS ---")
if not def_filtered.empty:
    print(def_filtered.to_string(index=False))
else:
    print("No defense data found for", player_name)

# --- DISPLAY ADVANCED DEFENSE STATS ---
print("\n--- ADVANCED DEFENSE STATS ---")
if not adv_def_filtered.empty:
    print(adv_def_filtered.to_string(index=False))
else:
    print("No advanced defense data found for", player_name)

# --- DISPLAY SNAP COUNTS ---
print("\n--- SNAP COUNTS ---")
if not snap_filtered.empty:
    row = snap_filtered.iloc[0]
    print(f"Offensive Snaps: {row.get('Off_Num', 'N/A')} ({row.get('Off_Pct', 'N/A')})")
    print(f"Defensive Snaps: {row.get('Def_Num', 'N/A')} ({row.get('Def_Pct', 'N/A')})")
    print(f"Special Teams:   {row.get('ST_Num', 'N/A')} ({row.get('ST_Pct', 'N/A')})")
else:
    print("No snap count data found for", player_name)

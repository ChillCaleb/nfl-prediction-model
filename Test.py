import pandas as pd
import ssl

# Temporary SSL bypass for local development (REMOVE IN PRODUCTION)
try:
    ssl._create_default_https_context = ssl._create_unverified_context
    print("[INFO] SSL certificate verification disabled temporarily.")
except Exception as e:
    print(f"[WARNING] Could not override SSL context: {e}")

def scrape_team_player_stats(team_abbr: str, year: int):
    """
    Scrape player stats for a given team and year from Pro-Football-Reference.

    Args:
        team_abbr (str): Team abbreviation (e.g., 'phi' for Eagles)
        year (int): Season year (e.g., 2023)

    Returns:
        pd.DataFrame: Cleaned player stats table
    """
    url = f"https://www.pro-football-reference.com/teams/{team_abbr}/{year}.htm"
    print(f"[INFO] Starting scrape for {team_abbr.upper()} {year}")
    print(f"[INFO] Target URL: {url}")

    # Read all tables on the page
    try:
        tables = pd.read_html(url)
        print(f"[INFO] Successfully loaded {len(tables)} tables from the page.")
    except ValueError as e:
        print(f"[ERROR] Failed to read tables: {e}")
        return None

    # Try to find the first table that includes a "Player" column
    player_stats = None
    print(f"[INFO] Searching for table with 'Player' column...")
    for idx, table in enumerate(tables):
        if "Player" in table.columns:
            player_stats = table
            print(f"[INFO] Found player stats table at index {idx}")
            break

    if player_stats is None:
        print(f"[ERROR] No player stats table with 'Player' column found.")
        return None

    print(f"[INFO] Cleaning table...")
    # Drop empty rows and columns
    initial_shape = player_stats.shape
    player_stats = player_stats.dropna(axis=0, how='all')
    player_stats = player_stats.dropna(axis=1, how='all')
    player_stats = player_stats[player_stats["Player"] != "Player"]
    player_stats.reset_index(drop=True, inplace=True)
    final_shape = player_stats.shape
    print(f"[INFO] Table cleaned: {initial_shape} -> {final_shape}")

    return player_stats

# === Run Script ===
if __name__ == "__main__":
    team = "phi"       # Philadelphia Eagles
    year = 2023

    print(f"[RUNNING] Scraper for team '{team.upper()}' in year {year}")
    df = scrape_team_player_stats(team, year)

    if df is not None:
        filename = f"{team}_{year}_player_stats.csv"
        try:
            df.to_csv(filename, index=False)
            print(f"[SUCCESS] Data saved to '{filename}'")
        except Exception as e:
            print(f"[ERROR] Failed to save CSV: {e}")

        print(f"[PREVIEW] First 5 rows:")
        print(df.head())
    else:
        print(f"[FAILURE] No data scraped for team '{team.upper()}' in year {year}")

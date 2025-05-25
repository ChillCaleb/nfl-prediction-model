import requests
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path
import sqlite3
import time
import os

DB_NAME = "nfl_player_data.db"

TEAM_ABBR_MAP = {
    "Cardinals": "crd", "Falcons": "atl", "Ravens": "rav", "Bills": "buf", "Panthers": "car",
    "Bears": "chi", "Bengals": "cin", "Browns": "cle", "Cowboys": "dal", "Broncos": "den",
    "Lions": "det", "Packers": "gnb", "Texans": "htx", "Colts": "clt", "Jaguars": "jax",
    "Chiefs": "kan", "Raiders": "rai", "Chargers": "sdg", "Rams": "ram", "Dolphins": "mia",
    "Vikings": "min", "Patriots": "nwe", "Saints": "nor", "Giants": "nyg", "Jets": "nyj",
    "Eagles": "phi", "Steelers": "pit", "49ers": "sfo", "Seahawks": "sea", "Buccaneers": "tam",
    "Titans": "oti", "Commanders": "was"
}

def get_connection():
    return sqlite3.connect(DB_NAME)

def scrape_and_store_snap_counts(team_name: str, year: int, output_dir="snap_counts"):
    team_abbr = TEAM_ABBR_MAP[team_name]
    url = f"https://www.pro-football-reference.com/teams/{team_abbr}/{year}-snap-counts.htm"

    print(f"\n📎 Scraping snap counts for {team_name} ({year})")
    response = requests.get(url)
    time.sleep(5)  # 5-second delay to avoid rate limits

    if response.status_code != 200:
        print(f"[ERROR] Failed to load {url} ({response.status_code})")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", {"id": "snap_counts"})

    if not table:
        print(f"[WARN] No snap count table found for {team_name}")
        return

    df = pd.read_html(str(table))[0]
    df.insert(0, "Team", team_name)
    df.insert(1, "Year", year)

    # Save as CSV
    os.makedirs(output_dir, exist_ok=True)
    csv_path = Path(output_dir) / f"{year}_{team_name.lower()}_snap_counts.csv"
    df.to_csv(csv_path, index=False)
    print(f"✅ CSV saved: {csv_path}")

    # Save to database
    table_name = f"team_{team_abbr}_snap_counts"
    with get_connection() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"💾 Stored in database table: {table_name}")

def main():
    year = 2024
    for team in TEAM_ABBR_MAP.keys():
        try:
            scrape_and_store_snap_counts(team, year)
        except Exception as e:
            print(f"[CRASH] Failed to scrape {team}: {e}")

if __name__ == "__main__":
    main()

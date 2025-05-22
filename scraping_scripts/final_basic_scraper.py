import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import os
import time
from pathlib import Path

def find_table_by_wrapper(soup, wrapper_id):
    print(f"🔍 Searching for wrapper div: {wrapper_id}")
    wrapper_div = soup.find("div", id=wrapper_id)
    if wrapper_div:
        table = wrapper_div.find("table")
        if table:
            print(f"✅ Found <table> inside {wrapper_id}")
        else:
            print(f"[WARN] Wrapper found but no <table> inside: {wrapper_id}")
        return table
    else:
        print(f"[WARN] Could not find wrapper div: {wrapper_id}")
    return None

TEAM_ABBR_MAP = {
    "Cardinals": "crd", "Falcons": "atl", "Ravens": "rav", "Bills": "buf", "Panthers": "car",
    "Bears": "chi", "Bengals": "cin", "Browns": "cle", "Cowboys": "dal", "Broncos": "den",
    "Lions": "det", "Packers": "gnb", "Texans": "htx", "Colts": "clt", "Jaguars": "jax",
    "Chiefs": "kan", "Raiders": "rai", "Chargers": "sdg", "Rams": "ram", "Dolphins": "mia",
    "Vikings": "min", "Patriots": "nwe", "Saints": "nor", "Giants": "nyg", "Jets": "nyj",
    "Eagles": "phi", "Steelers": "pit", "49ers": "sfo", "Seahawks": "sea", "Buccaneers": "tam",
    "Titans": "oti", "Commanders": "was"
}

def scrape_and_save_basic_stats_for_all_teams(nfl_root="NFL"):
    table_wrappers = {
        "all_passing": "passing",
        "all_rushing_and_receiving": "rushing_and_receiving",
        "all_returns": "returns",
        "all_kicking": "kicking",
        "all_punting": "punting",
        "all_defense": "defense",
        "all_snap_counts": "snap_counts"
    }

    nfl_path = Path(nfl_root)
    for conference in nfl_path.iterdir():
        if conference.is_dir():
            for division in conference.iterdir():
                if division.is_dir():
                    for team_path in division.iterdir():
                        if not team_path.is_dir():
                            continue

                        team_name = team_path.name
                        team_abbr = TEAM_ABBR_MAP.get(team_name)
                        if not team_abbr:
                            print(f"[SKIP] Unknown team abbreviation for: {team_name}")
                            continue

                        url = f"https://www.pro-football-reference.com/teams/{team_abbr}/2024.htm"
                        print(f"\n📎 Scraping basic stats for {team_name.upper()} ({team_abbr.upper()})")
                        print(f"🌐 URL: {url}")

                        try:
                            response = requests.get(url)
                            if response.status_code != 200:
                                print(f"[ERROR] Failed to load {url} (status {response.status_code})")
                                continue

                            soup = BeautifulSoup(response.content, "html.parser")

                            for wrapper_id, filename in table_wrappers.items():
                                print(f"\n⏳ Waiting 15 seconds before scraping: {filename}")
                                time.sleep(15)

                                table_html = find_table_by_wrapper(soup, wrapper_id)
                                if table_html is None:
                                    print(f"[❌] Skipping {filename} — table not found.\n")
                                    continue

                                df = pd.read_html(StringIO(str(table_html)))[0]
                                df.columns = df.columns.map(str)
                                df = df[df.columns.dropna()]
                                df = df[df[df.columns[0]] != df.columns[0]]

                                print(f"📋 Columns for {filename}: {list(df.columns)[:8]}")
                                print(df.head(2))

                                output_path = os.path.join(team_path, f"{filename}.csv")
                                df.to_csv(output_path, index=False)
                                print(f"💾 Saved to {output_path}")

                        except Exception as e:
                            print(f"[ERROR] Exception scraping {team_name}: {e}")

if __name__ == "__main__":
    scrape_and_save_basic_stats_for_all_teams(nfl_root="NFL")

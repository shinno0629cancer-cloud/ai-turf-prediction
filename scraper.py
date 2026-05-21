import time
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

class NetkeibaScraper:
    def __init__(self):
        self.base_url = "https://db.netkeiba.com/race/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }

    def scrape_race(self, race_id):
        url = f"{self.base_url}{race_id}/"
        try:
            response = requests.get(url, headers=self.headers)
            response.encoding = 'EUC-JP' # Netkeiba uses EUC-JP
            if response.status_code != 200:
                print(f"Failed to retrieve {url}")
                return None, None

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 1. Scrape Race Info (distance, condition, etc.)
            race_info = {}
            info_div = soup.find('div', class_='data_intro')
            if info_div:
                title = info_div.find('h1')
                race_info['race_name'] = title.text.strip() if title else ""
                
                detail_p = info_div.find('p', class_='diary_snap_cut')
                if detail_p:
                    detail_text = detail_p.text
                    # Extracting details using basic string operations/regex
                    # Example text: "芝右1600m / 天候 : 晴 / 芝 : 良 / 発走 : 15:40"
                    race_info['course_type'] = detail_text[0] if len(detail_text) > 0 else "" # 芝 or ダ
                    
                    # Regex for distance
                    dist_match = re.search(r'(\d+)m', detail_text)
                    race_info['distance'] = int(dist_match.group(1)) if dist_match else None
                    
                    # Weather and Track Condition
                    weather_match = re.search(r'天候 : (.*?)\s', detail_text)
                    race_info['weather'] = weather_match.group(1) if weather_match else ""
                    
                    condition_match = re.search(r'(芝|ダート) : (.*?)\s', detail_text)
                    race_info['track_condition'] = condition_match.group(2) if condition_match else ""

            # 2. Scrape Results Table using pandas
            try:
                # read_html returns a list of dataframes
                dfs = pd.read_html(response.text)
                if len(dfs) > 0:
                    results_df = dfs[0]
                    # Adding race_id to the dataframe
                    results_df['race_id'] = race_id
                    
                    # Convert to string and clean up some columns if necessary
                    return race_info, results_df
                else:
                    print(f"No tables found for {race_id}")
                    return race_info, None
            except ValueError:
                print(f"No tables found for {race_id} (ValueError)")
                return race_info, None

        except Exception as e:
            print(f"Error scraping {race_id}: {e}")
            return None, None

def generate_race_ids(year, place_codes, kai_range, day_range, race_range):
    """
    Generate possible race IDs.
    place_codes: list of strings e.g. ['05'] for Tokyo
    """
    race_ids = []
    for place in place_codes:
        for kai in range(1, kai_range + 1):
            for day in range(1, day_range + 1):
                for r in range(1, race_range + 1):
                    race_id = f"{year}{place}{kai:02d}{day:02d}{r:02d}"
                    race_ids.append(race_id)
    return race_ids

if __name__ == "__main__":
    scraper = NetkeibaScraper()
    
    # 試しに2023年の東京開催(05)、第1回、第1日〜第2日の1〜12レースを取得してみる
    test_race_ids = generate_race_ids('2023', ['05'], 1, 2, 12)
    
    all_results = []
    all_race_info = []

    print(f"Scraping {len(test_race_ids)} races...")
    
    for rid in test_race_ids:
        print(f"Scraping {rid}...")
        info, df = scraper.scrape_race(rid)
        if df is not None and len(df) > 0:
            # Combine info into dataframe
            for k, v in info.items():
                df[k] = v
            all_results.append(df)
        time.sleep(1) # Be polite to the server
        
    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        # Save to CSV
        output_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(output_dir, "historical_results.csv")
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"Successfully saved {len(final_df)} records to {output_file}")
    else:
        print("No valid data scraped.")

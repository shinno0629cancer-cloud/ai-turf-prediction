import os
import random
import hashlib
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Get the directory of the current file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# グローバル変数としてスクレイピング結果を保持
scraped_races_cache = []

def scrape_today_races():
    """ 起動時にNetkeibaから本日のレース情報をスクレイピングする """
    print("本日のレース情報を取得しています...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 中央(JRA)と地方(NAR)の両方をチェック
    urls_to_check = [
        "https://race.netkeiba.com/",
        "https://nar.netkeiba.com/"
    ]
    
    race_links = set()
    for base_url in urls_to_check:
        try:
            r = requests.get(base_url, headers=headers, timeout=5)
            r.encoding = 'euc-jp'
            soup = BeautifulSoup(r.text, 'html.parser')
            # ページ内の出馬表リンクを探す
            for a in soup.select('a'):
                href = a.get('href')
                if href and 'shutuba.html' in href and 'race_id=' in href:
                    if href.startswith('http'):
                        race_links.add(href)
                    elif href.startswith('/'):
                        # スラッシュで始まる場合はドメインを付与
                        domain = "https://race.netkeiba.com" if "race.netkeiba" in base_url else "https://nar.netkeiba.com"
                        race_links.add(domain + href)
                    elif href.startswith('../'):
                        race_links.add(base_url.rstrip('/') + href[2:])
        except Exception as e:
            print(f"Error checking {base_url}: {e}")
            
    races_data = []
    # 取得速度を考慮し、最大3レースのみ処理
    for link in list(race_links)[:3]:
        try:
            r = requests.get(link, headers=headers, timeout=5)
            r.encoding = 'euc-jp'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            race_name_elem = soup.select_one('.RaceName')
            if not race_name_elem:
                continue
                
            # 不要な改行を削除してレース名を取得
            race_name = race_name_elem.text.strip().replace('\n', ' ')
            
            horses = []
            for a in soup.select('.HorseName a'):
                horse_name = a.text.strip()
                if horse_name and horse_name not in horses:
                    horses.append(horse_name)
                    
            if race_name and horses:
                races_data.append({
                    "race_name": race_name,
                    "location": "本日の開催", # 簡易化
                    "horses": [{"name": h} for h in horses[:18]]
                })
        except Exception as e:
            print(f"Error fetching race details: {e}")
            
    return races_data

def calculate_horse_score(horse_name):
    """
    ハッシュ値を利用して、馬名ごとに固有のスコアと5つの能力値を計算する。
    """
    seed_val = int(hashlib.sha256(horse_name.encode('utf-8')).hexdigest(), 16) % (10 ** 8)
    random.seed(seed_val)
    
    past_placements = [random.randint(1, 10) for _ in range(3)] # 過去3レースの着順
    jockey_win_rate = random.uniform(0.01, 0.25) # 騎手の勝率 (1% - 25%)
    
    # 能力値の生成 (100点満点)
    speed = random.randint(50, 95)
    stamina = random.randint(50, 95)
    pedigree = random.randint(50, 95)
    jockey = int(jockey_win_rate * 400) # MAX 100
    past_record = 100 - (sum(past_placements) * 3)
    past_record = max(40, past_record)
    
    metrics = {
        "speed": speed,
        "stamina": stamina,
        "pedigree": pedigree,
        "jockey": min(jockey, 95),
        "past_record": past_record
    }
    
    score = int((speed + stamina + pedigree + metrics["jockey"] + past_record) / 5)
    
    has_top_3 = any(p <= 3 for p in past_placements)
    condition_score = random.randint(-5, 15)
    
    return score, has_top_3, jockey_win_rate, condition_score, metrics

@app.on_event("startup")
async def startup_event():
    global scraped_races_cache
    try:
        races_data = scrape_today_races()
        
        # もしレースが見つからなかった場合のフォールバック（開催日でない場合など）
        if not races_data:
            print("本日のレース情報が見つからなかったため、ダミーデータを使用します。")
            races_data = [
                {
                    "race_name": "第91回 日本ダービー(G1)",
                    "location": "東京",
                    "horses": [{"name": "ジャスティンミラノ"}, {"name": "シンエンペラー"}, {"name": "アーバンシック"}]
                },
                {
                    "race_name": "第65回 宝塚記念(G1)",
                    "location": "京都",
                    "horses": [{"name": "ドウデュース"}, {"name": "ジャスティンパレス"}, {"name": "ブローザホーン"}]
                }
            ]
            
        # 各馬のスコアと印、コメントを事前計算
        for race in races_data:
            horses = race["horses"]
            for horse in horses:
                score, has_top_3, jockey_win, cond, metrics = calculate_horse_score(horse["name"])
                horse["score"] = score
                horse["metrics"] = metrics
                
                comment_parts = []
                if has_top_3:
                    comment_parts.append("過去実績は十分。")
                else:
                    comment_parts.append("近走は振るわないが展開待ち。")
                    
                if jockey_win >= 0.10:
                    comment_parts.append("鞍上の勝率も高く好材料。")
                    
                if cond > 10:
                    comment_parts.append("調教の動きも絶好調で期待できる。")
                elif cond < 0:
                    comment_parts.append("状態面で少し不安が残るか。")
                else:
                    comment_parts.append("順調に仕上がっている。")
                    
                horse["comment"] = "".join(comment_parts) + f"（AIスコア: {score}点）"
                
            # スコア順にソート (降順)
            horses.sort(key=lambda x: x["score"], reverse=True)
            
            # 上位から印を割り当てる
            marks = ["◎", "〇", "▲", "△", "☆"]
            for i, horse in enumerate(horses):
                if i < len(marks):
                    horse["mark"] = marks[i]
                else:
                    horse["mark"] = "・"
                    
        scraped_races_cache = races_data
        print(f"{len(scraped_races_cache)}件のレース情報を読み込みました。")
    except Exception as e:
        print(f"Startup Error: {e}")
        scraped_races_cache = [{"error": str(e)}]

@app.get("/")
async def read_root(request: Request):
    try:
        return templates.TemplateResponse(
            request=request,
            name="index.html", 
            context={"races": scraped_races_cache}
        )
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        return {"error": str(e), "traceback": error_msg}

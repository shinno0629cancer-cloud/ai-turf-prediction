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
    """
    Yahoo!競馬から本日のレース情報（レース名、出走馬名など）をスクレイピングする
    """
    print("本日のレース情報を取得しています...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    races_data = []
    
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        import uuid
        
        # 1. トップページから開催競馬場のリストURLを取得
        top_url = "https://sports.yahoo.co.jp/keiba/"
        r_top = requests.get(top_url, headers=headers, timeout=5)
        soup_top = BeautifulSoup(r_top.text, 'html.parser')
        
        venue_links = set()
        for a in soup_top.select('a'):
            href = a.get('href')
            if href and '/race/list/' in href:
                venue_links.add(requests.compat.urljoin(top_url, href))
                
        # 2. 各競馬場ページから全レースの出馬表URLを取得
        denma_links = set()
        for v_link in venue_links:
            try:
                r_v = requests.get(v_link, headers=headers, timeout=5)
                soup_v = BeautifulSoup(r_v.text, 'html.parser')
                
                venue_title = soup_v.title.string if soup_v.title else ""
                match = re.search(r'競馬 - (.*?) (.*?) レース一覧', venue_title)
                if match:
                    race_date = match.group(1).strip()
                    location = match.group(2).strip()
                else:
                    race_date = "近日開催"
                    location = "競馬場"
                    
                for a in soup_v.select('a'):
                    href = a.get('href')
                    if href and '/race/index/' in href:
                        # /index/ を /denma/ に置換して出馬表ページのURLにする
                        denma_url = requests.compat.urljoin("https://sports.yahoo.co.jp", href.replace('/index/', '/denma/'))
                        denma_links.add((denma_url, race_date, location))
            except Exception as e:
                print(f"Error checking venue {v_link}: {e}")
                
        # 3. 各出馬表ページからレース名と馬名を抽出
        for link, race_date, location in list(denma_links):
            try:
                r = requests.get(link, headers=headers, timeout=5)
                soup = BeautifulSoup(r.text, 'html.parser')
                
                # レース名をタイトルから取得
                title_text = soup.title.string if soup.title else ""
                if "出馬表" not in title_text:
                    continue
                    
                # 「競馬 - 2026年優駿牝馬 出馬表 - スポーツナビ」などのフォーマットから抽出
                parts = title_text.split('-')
                if len(parts) >= 2:
                    race_name = parts[1].replace('出馬表', '').strip()
                else:
                    race_name = "不明なレース"
                    
                # 馬名を取得
                horses = []
                for a in soup.select('td.hr-table__data--name a'):
                    if '/horse/' in a.get('href', ''):
                        horse_name = a.text.strip()
                        if horse_name and horse_name not in horses:
                            horses.append(horse_name)
                            
                if race_name and horses:
                    races_data.append({
                        "race_id": str(uuid.uuid4())[:8],
                        "date": race_date,
                        "race_name": race_name,
                        "location": location,
                        "horses": [{"name": h} for h in horses[:18]]
                    })
            except Exception as e:
                print(f"Error scraping race {link}: {e}")
                
    except Exception as e:
        print(f"Error checking top page: {e}")
        
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
    
    # 新ロジック: 勝率重視の重み付け (スピードと騎手を高く評価)
    true_score = (metrics["speed"] * 2.0) + (metrics["jockey"] * 1.5) + (metrics["stamina"] * 1.0) + (metrics["past_record"] * 0.5) + (metrics["pedigree"] * 0.5)
    
    # 100点満点スケールにざっくり調整
    score = int(true_score / 5.5)
    
    has_top_3 = any(p <= 3 for p in past_placements)
    condition_score = random.randint(-5, 15)
    
    return score, has_top_3, jockey_win_rate, condition_score, metrics

@app.on_event("startup")
async def startup_event():
    global scraped_races_cache
    try:
        races_data = scrape_today_races()
        

            
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
        grouped = {}
        valid_races = 0
        for r in scraped_races_cache:
            if "error" in r: continue
            valid_races += 1
            d = r.get("date", "開催日不明")
            l = r.get("location", "競馬場不明")
            if d not in grouped: grouped[d] = {}
            if l not in grouped[d]: grouped[d][l] = []
            grouped[d][l].append(r)
            
        # レース名に含まれる数字(1Rなど)でソートする関数
        import re
        def get_race_num(name):
            m = re.search(r'(\d+)R', name)
            return int(m.group(1)) if m else 999
            
        for d in grouped:
            for l in grouped[d]:
                grouped[d][l].sort(key=lambda x: get_race_num(x['race_name']))
                
        return templates.TemplateResponse(
            request=request,
            name="index.html", 
            context={"grouped_races": grouped, "has_races": valid_races > 0}
        )
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        return {"error": str(e), "traceback": error_msg}

@app.get("/race/{race_id}")
async def read_race(request: Request, race_id: str):
    race_data = next((r for r in scraped_races_cache if r.get("race_id") == race_id), None)
    if not race_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Race not found")
        
    return templates.TemplateResponse(
        request=request,
        name="race_detail.html",
        context={"race": race_data}
    )

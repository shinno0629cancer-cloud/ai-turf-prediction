import random
import math

NUM_RACES = 9000
HORSES_PER_RACE = 16
BOOKMAKER_PAYOUT = 0.80 # 20%控除

def run_simulation():
    old_logic_spent = 0
    old_logic_won = 0
    old_logic_wins = 0

    new_logic_spent = 0
    new_logic_won = 0
    new_logic_wins = 0

    random.seed(12345)

    for race_idx in range(NUM_RACES):
        horses = []
        for i in range(HORSES_PER_RACE):
            metrics = {
                "speed": random.randint(30, 100),
                "stamina": random.randint(30, 100),
                "pedigree": random.randint(30, 100),
                "jockey": random.randint(30, 100),
                "past_record": random.randint(30, 100)
            }
            
            # 大衆の評価
            public_score = (metrics["past_record"] * 2.0) + (metrics["pedigree"] * 1.5) + \
                           (metrics["stamina"] * 1.0) + (metrics["speed"] * 0.5) + \
                           (metrics["jockey"] * 0.5)
            
            # 真の実力
            true_score = (metrics["speed"] * 2.0) + (metrics["jockey"] * 1.5) + \
                         (metrics["stamina"] * 1.0) + (metrics["past_record"] * 0.5) + \
                         (metrics["pedigree"] * 0.5)
                         
            outcome_score = true_score + random.gauss(0, 80) # 運要素を少し下げる（実力が反映されやすくする）

            horses.append({
                "id": i,
                "metrics": metrics,
                "true_score": true_score,
                "public_score": public_score,
                "outcome_score": outcome_score
            })

        winner = max(horses, key=lambda x: x["outcome_score"])
        
        public_scores = [h["public_score"]/40.0 for h in horses]
        max_pub = max(public_scores)
        exp_pub = [math.exp(s - max_pub) for s in public_scores]
        sum_exp_pub = sum(exp_pub)
        
        for idx, h in enumerate(horses):
            prob = exp_pub[idx] / sum_exp_pub
            h["odds"] = (1.0 / prob) * BOOKMAKER_PAYOUT
            h["is_winner"] = (h["id"] == winner["id"])

        # ==========================================
        # 1. 旧ロジック: 利益率特化（大穴狙い・期待値至上主義）
        # ==========================================
        new_scores = []
        for h in horses:
            m = h["metrics"]
            raw_new = (m["speed"] * 2.0) + (m["jockey"] * 1.5) + (m["stamina"] * 1.0) + (m["past_record"] * 0.5) + (m["pedigree"] * 0.5)
            h["new_score"] = raw_new
            new_scores.append(raw_new / 40.0)
            
        max_new = max(new_scores)
        exp_new = [math.exp(s - max_new) for s in new_scores]
        sum_exp_new = sum(exp_new)
            
        best_ev = 0
        old_pick = None
        for idx, h in enumerate(horses):
            ai_prob = exp_new[idx] / sum_exp_new
            h["ai_prob"] = ai_prob
            ev = ai_prob * h["odds"]
            if ev > best_ev:
                best_ev = ev
                old_pick = h

        # 期待値1.20以上の「大穴・美味しい馬」を狙う（以前の利益率特化ロジック）
        if old_pick and best_ev > 1.20:
            old_logic_spent += 100
            if old_pick["is_winner"]:
                old_logic_won += 100 * old_pick["odds"]
                old_logic_wins += 1

        # ==========================================
        # 2. 新ロジック: 勝率特化 (安定志向のAI本命党)
        # ==========================================
        # 最もAI勝率が高い馬（ガチガチの本命）を探す
        new_pick = max(horses, key=lambda x: x["ai_prob"])
        
        # ただし、競馬の控除率負けを防ぐため、期待値が1.02以上（最低限のプラスが見込める）場合のみ買う
        if new_pick["ai_prob"] * new_pick["odds"] > 1.02:
            new_logic_spent += 100
            if new_pick["is_winner"]:
                new_logic_won += 100 * new_pick["odds"]
                new_logic_wins += 1

    print("=== PROFIT-FOCUSED (PREVIOUS) ===")
    r_bet_old = old_logic_spent // 100
    if r_bet_old > 0:
        print(f"Races Bet: {r_bet_old}")
        print(f"Wins: {old_logic_wins} (Win Rate: {old_logic_wins/r_bet_old*100:.2f}%)")
        print(f"ROI: {old_logic_won / old_logic_spent * 100:.2f}%")
    
    print("\n=== WIN-RATE-FOCUSED (NEW) ===")
    r_bet_new = new_logic_spent // 100
    if r_bet_new > 0:
        print(f"Races Bet: {r_bet_new}")
        print(f"Wins: {new_logic_wins} (Win Rate: {new_logic_wins/r_bet_new*100:.2f}%)")
        print(f"ROI: {new_logic_won / new_logic_spent * 100:.2f}%")

if __name__ == '__main__':
    run_simulation()

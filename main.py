import os
import random
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

games_db: Dict[str, dict] = {}

total_games = 0
wins = 0

class NewGameRequest(BaseModel):
    hard_mode: bool = False

class GuessRequest(BaseModel):
    game_id: str
    guess: str
class StatsResponse(BaseModel):
    total_games: int
    wins: int
    win_rate: float

@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """ 取得全域勝率統計資訊 """
    win_rate = round((wins / total_games * 100), 1) if total_games > 0 else 0.0
    return {
        "total_games": total_games,
        "wins": wins,
        "win_rate": win_rate
    }

@app.post("/api/new-game")
def start_new_game(hard_mode: bool = False):
    """ 建立新一局遊戲，支援透過 Query 參數接收 hard_mode (預設 False) """
    global total_games
    total_games += 1

    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "counted_win": False,
        "hard_mode": hard_mode,
        "revealed_greens": {}
    }
    return {"game_id": game_id, "hard_mode": hard_mode, "message": "New game started!"}

@app.post("/api/guess")
def process_guess(req: GuessRequest):
    global wins
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in directory")

    game_data = games_db[game_id]
    target = game_data["target"]

    # ---------------------------------------------------------
    # 【任務四】Hard Mode 邏輯驗證
    # ---------------------------------------------------------
    if game_data["hard_mode"]:
        revealed_greens = game_data["revealed_greens"]
        for idx_str, char in revealed_greens.items():
            idx = int(idx_str)
            if guess[idx] != char:
                raise HTTPException(
                    status_code=400, 
                    detail="Hard Mode: Must use revealed hint at green position"
                )

    game_data["attempts"] += 1
    attempts = game_data["attempts"]

    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            # 記錄綠色位置供後續硬核模式檢查
            game_data["revealed_greens"][str(i)] = guess[i]

    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    is_correct = (guess == target)
    game_over = is_correct or (attempts >= 6)

    if is_correct and not game_data["counted_win"]:
        game_data["status"] = "WON"
        game_data["counted_win"] = True
        wins += 1
    elif attempts >= 6:
        game_data["status"] = "LOST"

    target_word_response = target if game_over else None
    win_rate = round((wins / total_games * 100), 1) if total_games > 0 else 0.0

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": target_word_response,
        "total_games": total_games,
        "wins": wins,
        "win_rate": win_rate
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

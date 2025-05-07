import os
import json
import pandas as pd

INPUT_DIR = "box_scores_app/data/weeks_2025"
OUTPUT_FILE = "box_scores_app/data/boxscores_2025.csv"

def flatten_game_data(game):
    def b(val):
        return int(bool(val)) if val is not None else None

    return {
        "id": game.get("id"),
        "season": game.get("season"),
        "week": game.get("week"),
        "seasonType": game.get("seasonType"),
        "startDate": game.get("startDate"),
        "completed": b(game.get("completed")),
        "neutralSite": b(game.get("neutralSite")),
        "conferenceGame": b(game.get("conferenceGame")),
        "venue": game.get("venue"),
        "homeTeam": game.get("homeTeam"),
        "homeConference": game.get("homeConference"),
        "homePoints": game.get("homePoints"),
        "homeLineScores": game.get("homeLineScores"),
        "awayTeam": game.get("awayTeam"),
        "awayConference": game.get("awayConference"),
        "awayPoints": game.get("awayPoints"),
        "awayLineScores": game.get("awayLineScores"),
    }

def compile_season():
    all_games = []
    for file in sorted(os.listdir(INPUT_DIR)):
        if file.endswith(".json"):
            with open(os.path.join(INPUT_DIR, file), "r") as f:
                week_data = json.load(f)
                all_games.extend([flatten_game_data(g) for g in week_data])
    df = pd.DataFrame(all_games)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Compiled {len(df)} games to {OUTPUT_FILE}")

if __name__ == "__main__":
    compile_season()

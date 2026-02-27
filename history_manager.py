import json
from pathlib import Path
from typing import List, Dict, Optional

class HistoryManager:
    def __init__(self, user_id: str):
        self.file_path = Path(f"history_{user_id}.jsonl")
        self.file_path.touch(exist_ok=True)

    def get_recent_history(self, days: int = 5) -> List[Dict]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, "r") as f:
            lines = list(f)[-days:]
            return [json.loads(line.strip()) for line in lines if line.strip()]

    def save_plan(self, plan: Dict, completion: Optional[Dict] = None):
        entry = {
            "date": plan["date"],
            "generated_plan": plan,
            "completion": completion
        }
        with open(self.file_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
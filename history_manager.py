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
            "completion": completion,
        }
        with open(self.file_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def save_completion(self, date: str, completion_data: Dict) -> bool:
        if not self.file_path.exists():
            return False

        lines = self.file_path.read_text().strip().splitlines()
        updated = False

        with open(self.file_path, "w") as f:
            for line in lines:
                entry = json.loads(line)
                if entry.get("date") == date and entry.get("completion") is None:
                    entry["completion"] = completion_data
                    updated = True
                f.write(json.dumps(entry) + "\n")

        if not updated:
            standalone = {
                "date": date,
                "generated_plan": None,
                "completion": completion_data,
            }
            with open(self.file_path, "a") as f:
                f.write(json.dumps(standalone) + "\n")

        return updated

    def get_entry_for_date(self, date: str) -> Optional[Dict]:
        if not self.file_path.exists():
            return None
        with open(self.file_path, "r") as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("date") == date:
                    return entry
        return None
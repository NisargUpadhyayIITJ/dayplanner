import os
import json
from dotenv import load_dotenv
load_dotenv()

from critic import Critic
from models import DailyRoutine
from rl_models import CompletionLog

with open("history_upadhyay_nisarg.jsonl", "r") as f:
    lines = f.readlines()

critic = Critic(model="gemini-2.5-flash")

for i, line in enumerate(lines):
    if not line.strip():
        continue
    entry = json.loads(line)
    if entry.get("completion") is None:
        continue
        
    plan = DailyRoutine.model_validate(entry["generated_plan"])
    completion = CompletionLog.model_validate(entry["completion"])

    try:
        print(f"Evaluating entry {i}...")
        eval_obj = critic.evaluate(plan, completion, [])
        print(f"Success for entry {i}")
    except Exception as e:
        print(f"Error on entry {i}")
        import traceback
        traceback.print_exc()

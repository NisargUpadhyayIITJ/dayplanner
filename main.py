from fastapi import FastAPI
from .models import DailyInput, DailyRoutine
from .llm_engine import LLMScheduler
from .history_manager import HistoryManager

app = FastAPI(title="ChronoForge Direction Engine")

llm = LLMScheduler()

@app.post("/generate_daily_routine", response_model=DailyRoutine)
async def generate_daily_routine(input_data: DailyInput):
    history_mgr = HistoryManager(input_data.user_id)
    recent_history = history_mgr.get_recent_history(days=5)

    routine = llm.generate_routine(input_data, recent_history)

    # Save generated plan (completion will be added later via /log_completion)
    history_mgr.save_plan(routine.model_dump())

    return routine


@app.post("/log_completion")
async def log_completion(user_id: str, date: str, completion: Dict):
    history_mgr = HistoryManager(user_id)
    # In a real system you would merge with existing entry, but for MVP we just print/log
    print(f"✅ Completion logged for {date} by {user_id}")
    # Optionally trigger nightly learning here
    return {"status": "logged"}
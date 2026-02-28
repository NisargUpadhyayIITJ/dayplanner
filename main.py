import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, HTTPException
from typing import Dict, Any

from models import DailyInput, DailyRoutine
from rl_models import CompletionLog, CriticEvaluation
from llm_engine import LLMScheduler
from history_manager import HistoryManager
from policy_store import PolicyStore
from critic import Critic

app = FastAPI(title="ChronoForge Direction Engine")

llm = LLMScheduler()
critic = Critic()


# ── Actor endpoint ───────────────────────────────────────────────────

@app.post("/generate_daily_routine", response_model=DailyRoutine)
async def generate_daily_routine(input_data: DailyInput):
    history_mgr = HistoryManager(input_data.user_id)
    recent_history = history_mgr.get_recent_history(days=5)

    # Load learned policy rules and inject into the Actor's prompt
    policy = PolicyStore(input_data.user_id)
    policy_block = policy.get_policy_prompt_block()

    routine = llm.generate_routine(input_data, recent_history, policy_block=policy_block)

    # Save generated plan (completion will be added later via /log_completion)
    history_mgr.save_plan(routine.model_dump())

    return routine


# ── Completion logging ───────────────────────────────────────────────

@app.post("/log_completion")
async def log_completion(completion: CompletionLog):
    """Accept a structured CompletionLog and merge it into the user's history."""
    history_mgr = HistoryManager(completion.user_id)
    found = history_mgr.save_completion(completion.date, completion.model_dump())

    status = "merged_with_plan" if found else "saved_standalone"
    print(f"✅ Completion logged for {completion.date} by {completion.user_id} ({status})")

    return {"status": status, "date": completion.date}


# ── Critic / Reflection endpoint ─────────────────────────────────────

@app.post("/trigger_reflection", response_model=CriticEvaluation)
async def trigger_reflection(user_id: str, date: str):
    """
    Run the Critic on a specific day's plan + completion.
    Updates the user's policy store with the proposed rules.
    """
    history_mgr = HistoryManager(user_id)
    entry = history_mgr.get_entry_for_date(date)

    if entry is None:
        raise HTTPException(status_code=404, detail=f"No history entry found for {date}")
    if entry.get("completion") is None:
        raise HTTPException(status_code=400, detail=f"No completion data for {date}. Log completion first.")
    if entry.get("generated_plan") is None:
        raise HTTPException(status_code=400, detail=f"No generated plan for {date}. Cannot reflect without a plan.")

    # Reconstruct models
    plan = DailyRoutine.model_validate(entry["generated_plan"])
    completion = CompletionLog.model_validate(entry["completion"])

    # Load existing policy
    policy = PolicyStore(user_id)
    existing_rules = policy.get_all_rules()

    # Run the Critic
    evaluation = critic.evaluate(plan, completion, existing_rules)

    # Update policy store with proposed rules
    policy.update_rules(evaluation.proposed_rules)

    print(f"🧠 Reflection complete for {date} by {user_id}: score={evaluation.performance_score}")
    return evaluation


# ── Policy inspection ────────────────────────────────────────────────

@app.get("/view_policy/{user_id}")
async def view_policy(user_id: str):
    """Return the current learned scheduling policy for a user."""
    policy = PolicyStore(user_id)
    return policy.to_dict()
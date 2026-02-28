import os
from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, HTTPException
from typing import Dict, Any

from models import DailyInput, DailyRoutine, RoutineResponse
from rl_models import CompletionLog, CriticEvaluation
from llm_engine import LLMScheduler
from history_manager import HistoryManager
from policy_store import PolicyStore
from critic import Critic

app = FastAPI(title="ChronoForge Direction Engine")

llm = LLMScheduler()
critic = Critic()


# ── Actor endpoint ───────────────────────────────────────────────────

@app.post("/generate_daily_routine", response_model=RoutineResponse)
async def generate_daily_routine(input_data: DailyInput):
    """
    Generate an optimised daily routine.

    Accepts the extended DailyInput (now includes `apps_to_align_with_focus_timer`
    and `archetype`) and returns a RoutineResponse envelope with:
      - data.meta          – institution / program / semester metadata
      - data.suggested_timetable – normalised weekly timetable
      - data.scheduled_tasks     – today's minute-by-minute plan
      - data.warnings            – any conflicts or attendance risks
    """
    print(f"---- GENERATE DAILY ROUTINE INPUT ----\n{input_data.model_dump_json(indent=2)}\n--------------------------------------")

    history_mgr = HistoryManager(input_data.user_id)
    recent_history = history_mgr.get_recent_history(days=5)

    # Load learned policy rules and inject into the Actor's prompt
    policy = PolicyStore(input_data.user_id)
    policy_block = policy.get_policy_prompt_block()

    routine_response: RoutineResponse = llm.generate_routine(
        input_data, recent_history, policy_block=policy_block
    )

    print(f"---- GENERATE DAILY ROUTINE OUTPUT ----\n{routine_response.model_dump_json(indent=2)}\n---------------------------------------")

    # Persist the generated plan (completion merged later via /log_completion)
    plan_dict = {
        "date": input_data.current_date,
        "scheduled_tasks": [t.model_dump() for t in routine_response.data.scheduled_tasks],
        "metadata": {
            "confidence_score": routine_response.data.meta.confidence,
            "energy_peak_utilized": True,
        },
    }
    history_mgr.save_plan(plan_dict)

    return routine_response


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

    plan = DailyRoutine.model_validate(entry["generated_plan"])
    completion = CompletionLog.model_validate(entry["completion"])

    policy = PolicyStore(user_id)
    existing_rules = policy.get_all_rules()

    evaluation = critic.evaluate(plan, completion, existing_rules)

    policy.update_rules(evaluation.proposed_rules)

    print(f"🧠 Reflection complete for {date} by {user_id}: score={evaluation.performance_score}")
    return evaluation


# ── Policy inspection ────────────────────────────────────────────────

@app.get("/view_policy/{user_id}")
async def view_policy(user_id: str):
    """Return the current learned scheduling policy for a user."""
    policy = PolicyStore(user_id)
    return policy.to_dict()



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8022, reload=True)
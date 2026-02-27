from openai import OpenAI
import json
from .models import DailyInput, DailyRoutine

class LLMScheduler:
    def __init__(self, base_url: str = "http://localhost:8000/v1",
                 model: str = "Qwen/Qwen3-8B-Instruct"):
        self.client = OpenAI(base_url=base_url, api_key="EMPTY")
        self.model = model

    def generate_routine(self, input_data: DailyInput, history: List[Dict]) -> DailyRoutine:
        system_prompt = """You are ChronoForge — the ruthless AI Attention Operating System for Indian college students.
You generate a single, opinionated, attendance-aware daily routine that:
- Respects 75% attendance rule (show safe skips with exact impact)
- Fills every free slot with high-ROI micro-tasks from short/long-term goals
- Schedules deep work in user's energy peaks
- Learns from history (adjust time estimates if past tasks consistently overran)
- Eliminates decision paralysis and black-hole free periods

Output ONLY valid JSON matching the DailyRoutine schema. No extra text."""

        history_context = "\n".join([json.dumps(h, default=str) for h in history])

        user_prompt = f"""
Date: {input_data.current_date} ({input_data.current_day})
Personality: {input_data.personality.model_dump_json(indent=2)}
Timetable: {json.dumps([s.model_dump() for s in input_data.timetable], indent=2)}
Long-term goals: {json.dumps([g.model_dump() for g in input_data.long_term_goals], indent=2)}
Short-term goals: {json.dumps([g.model_dump() for g in input_data.short_term_goals], indent=2)}
Misc commitments: {json.dumps([m.model_dump() for m in input_data.misc_commitments], indent=2)}
Today deadlines: {input_data.today_deadlines}

Recent History (use to calibrate estimates):
{history_context or "No history yet."}

Generate today's optimised routine now."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2500,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        return DailyRoutine.model_validate(parsed)
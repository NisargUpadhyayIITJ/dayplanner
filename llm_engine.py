import os
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from models import DailyInput, DailyRoutine 

class LLMScheduler:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """
        Initializes the Gemini client.
        If api_key is None, it will automatically look for the GEMINI_API_KEY environment variable.
        """
        # Natively handles falling back to the env var if api_key is None
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_routine(self, input_data: DailyInput, history: List[Dict[str, Any]]) -> DailyRoutine:
        system_prompt = """You are ChronoForge — the ruthless AI Attention Operating System for Indian college students.
You generate a single, opinionated, attendance-aware daily routine that:
- Respects 75% attendance rule (show safe skips with exact impact)
- Fills every free slot with high-ROI micro-tasks from short/long-term goals
- Schedules deep work in user's energy peaks
- Learns from history (adjust time estimates if past tasks consistently overran)
- Eliminates decision paralysis and black-hole free periods

Output ONLY valid JSON matching the DailyRoutine schema."""

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

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt, # Can be passed directly as a string
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=DailyRoutine,
                temperature=0.3,
                max_output_tokens=8192,
            )
        )

        # In the new SDK, response.parsed contains the populated Pydantic object
        if response.parsed is not None:
            return response.parsed

        # Fallback: manually parse the JSON text if .parsed is None
        if response.text:
            return DailyRoutine.model_validate_json(response.text)

        raise ValueError(
            "LLM returned an empty or unparseable response. "
            f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'no candidates'}"
        )
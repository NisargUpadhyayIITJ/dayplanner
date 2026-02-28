import os
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from models import (
    DailyInput, DailyRoutine, RoutineResponse, RoutineResponseData,
    TimetableMeta, SuggestedTimetableEntry, ScheduledTask
)
from datetime import datetime
from schedule_fixer import build_collision_free_schedule


# ── Internal LLM output schema (what the LLM actually generates) ─────

from pydantic import BaseModel, Field

class _LLMOutput(BaseModel):
    """Schema the LLM must return — we convert this to RoutineResponse."""
    date: str
    scheduled_tasks: List[ScheduledTask]
    metadata_confidence_score: float = 0.9
    metadata_energy_peak_utilized: bool = True
    suggested_timetable: List[SuggestedTimetableEntry] = Field(default_factory=list)
    institution: str = "Unknown Institution"
    program: str = "Unknown Program"
    semester: str = "Unknown Semester"
    section: str = "Unknown Section"
    timezone: str = "Asia/Kolkata"
    warnings: List[str] = Field(default_factory=list)
    message: str = "Timetable extracted and normalized successfully"


class LLMScheduler:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3-flash-preview"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_routine(
        self,
        input_data: DailyInput,
        history: List[Dict[str, Any]],
        policy_block: str = "",
    ) -> RoutineResponse:
        """
        Generate a full daily routine and return it wrapped in the new
        RoutineResponse envelope.
        """

        archetype_note = (
            f"\nUser archetype: {input_data.archetype}. "
            "Tailor energy blocks and task ordering to this archetype's tendencies."
            if input_data.archetype
            else ""
        )

        focus_apps_note = (
            f"\nApps to align with focus timer (block during deep-work): "
            f"{', '.join(input_data.apps_to_align_with_focus_timer)}."
            if input_data.apps_to_align_with_focus_timer
            else ""
        )

        system_prompt = f"""You are ChronoForge — the ruthless AI Attention Operating System for Indian college students.
You generate a single, opinionated, attendance-aware daily routine that:
- Respects 75% attendance rule (show safe skips with exact impact)
- Fills every free slot with high-ROI micro-tasks from short/long-term goals
- Schedules deep work in user's energy peaks
- Learns from history (adjust time estimates if past tasks consistently overran)
- Eliminates decision paralysis and black-hole free periods
- Honours focus-timer app blocking for distraction control
{archetype_note}
{focus_apps_note}
"""

        if policy_block:
            system_prompt += policy_block

        system_prompt += """
You must also output a `suggested_timetable` — a week-level normalized class timetable
derived from the user's provided timetable slots (expand per-day slots into a full weekly
view across Monday-Saturday). Infer `institution`, `program`, `semester`, `section` from
context or use sensible defaults. Add `warnings` for any conflicts, attendance risks, or
ambiguous slots.

Output ONLY valid JSON matching the _LLMOutput schema.
"""

        history_context = "\n".join([json.dumps(h, default=str) for h in history])

        user_prompt = f"""
Date: {input_data.current_date} ({input_data.current_day})
Personality: {input_data.personality.model_dump_json(indent=2)}
Archetype: {input_data.archetype or "not specified"}
Timetable: {json.dumps([s.model_dump() for s in input_data.timetable], indent=2)}
Long-term goals: {json.dumps([g.model_dump() for g in input_data.long_term_goals], indent=2)}
Short-term goals: {json.dumps([g.model_dump() for g in input_data.short_term_goals], indent=2)}
Misc commitments: {json.dumps([m.model_dump() for m in input_data.misc_commitments], indent=2)}
Apps to block during focus: {json.dumps(input_data.apps_to_align_with_focus_timer)}
Today deadlines: {json.dumps(input_data.today_deadlines or [])}

Recent History (use to calibrate estimates):
{history_context or "No history yet."}

Generate today's optimised routine now. Also produce a suggested_timetable for the full week
based on the timetable slots provided, expanding them across all weekdays logically.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=_LLMOutput,
                temperature=0.3,
                max_output_tokens=65536,
            ),
        )

        if response.parsed is not None:
            raw: _LLMOutput = response.parsed
        elif response.text:
            raw = _LLMOutput.model_validate_json(response.text)
        else:
            raise ValueError(
                "LLM returned an empty or unparseable response. "
                f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'no candidates'}"
            )

        # ── Post-process: inject classes + resolve collisions (pure logic) ──
        fixed_tasks = build_collision_free_schedule(
            llm_tasks=raw.scheduled_tasks,
            timetable_entries=input_data.timetable,
        )

        # ── Build RoutineResponse from _LLMOutput ──────────────────
        meta = TimetableMeta(
            institution=raw.institution,
            program=raw.program,
            semester=raw.semester,
            section=raw.section,
            generated_at=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            timezone=raw.timezone,
            confidence=raw.metadata_confidence_score,
        )

        response_data = RoutineResponseData(
            meta=meta,
            suggested_timetable=raw.suggested_timetable,
            scheduled_tasks=fixed_tasks,
            warnings=raw.warnings,
        )

        return RoutineResponse(
            success=True,
            data=response_data,
            message=raw.message,
        )

    # ── Legacy helper: returns a plain DailyRoutine (used by Critic) ─

    def generate_routine_plain(
        self,
        input_data: DailyInput,
        history: List[Dict[str, Any]],
        policy_block: str = "",
    ) -> DailyRoutine:
        """Thin wrapper that strips the envelope for internal Critic use."""
        full = self.generate_routine(input_data, history, policy_block)
        from models import RoutineMetadata
        return DailyRoutine(
            date=input_data.current_date,
            scheduled_tasks=full.data.scheduled_tasks,
            metadata=RoutineMetadata(
                confidence_score=full.data.meta.confidence,
                energy_peak_utilized=True,
            ),
        )
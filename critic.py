import os
import json
from typing import List, Optional
from google import genai
from google.genai import types

from models import DailyRoutine
from rl_models import CompletionLog, CriticEvaluation, PolicyRule


class Critic:
    """
    The Critic evaluates how well the user followed the Actor's generated plan,
    identifies patterns, and proposes scheduling policy rules.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def evaluate(
        self,
        plan: DailyRoutine,
        completion: CompletionLog,
        existing_rules: List[PolicyRule],
    ) -> CriticEvaluation:
        """Run the Critic LLM to produce an evaluation + proposed rule updates."""

        existing_rules_text = "\n".join(
            f"- [{r.category}] (confidence={r.confidence:.2f}) {r.rule_text}"
            for r in existing_rules
        ) or "No existing rules yet."

        system_prompt = """You are the Critic in an Actor-Critic reinforcement-learning loop for a college student's daily planner called ChronoForge.

Your job:
1. Compare the PLANNED schedule against what the student ACTUALLY completed.
2. Identify patterns: time-estimation accuracy, energy/focus mismatches, attendance impact, recurring skips.
3. Score overall performance (0-100).
4. Produce CONCRETE, ACTIONABLE scheduling rules the Actor should follow in future plans.
5. Review existing rules: reinforce ones the data supports (bump confidence), revise ones the data contradicts, and propose brand-new ones.

Rule guidelines:
- Each rule must have a unique rule_id (use format: rule_<category>_<3-digit-number>).
- Set confidence between 0.0 and 1.0 — higher = more evidence.
- Categories: time_estimation, energy_management, task_priority, attendance, general.
- Keep rules short, specific, and actionable (one sentence each).
- Do NOT propose more than 5 new rules per reflection.

Output ONLY valid JSON matching the CriticEvaluation schema."""

        user_prompt = f"""
## Generated Plan
{json.dumps(plan.model_dump(), indent=2, default=str)}

## User Completion Log
{json.dumps(completion.model_dump(), indent=2, default=str)}

## Existing Policy Rules
{existing_rules_text}

Evaluate the day and produce your CriticEvaluation now."""

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=CriticEvaluation,
                temperature=0.4,
                max_output_tokens=4096,
            ),
        )

        if response.parsed is not None:
            return response.parsed

        if response.text:
            return CriticEvaluation.model_validate_json(response.text)

        raise ValueError(
            "Critic LLM returned an empty or unparseable response. "
            f"Finish reason: {response.candidates[0].finish_reason if response.candidates else 'no candidates'}"
        )

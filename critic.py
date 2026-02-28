import os
import json
import re
from typing import List, Optional
from google import genai
from google.genai import types

from models import DailyRoutine
from rl_models import CompletionLog, CriticEvaluation, PolicyRule


def _repair_truncated_json(raw: str) -> str:
    """
    Best-effort repair for JSON that was cut off mid-stream by a token limit.
    Strategy:
      1. Strip any trailing partial string/key.
      2. Close every open array and object in LIFO order.
    Returns a string that is more likely to parse correctly.
    """
    text = raw.strip()

    # Remove a trailing incomplete string value (e.g.  "category": "gene  )
    text = re.sub(r',\s*"[^"]*$', '', text)   # dangling key-value pair
    text = re.sub(r'"[^"]*$', '"_truncated"', text)  # dangling string value

    # Track open braces/brackets and close them
    stack = []
    in_string = False
    escape_next = False
    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append('}' if ch == '{' else ']')
        elif ch in ('}', ']'):
            if stack and stack[-1] == ch:
                stack.pop()

    # Close everything that was left open (in reverse order)
    closing = ''.join(reversed(stack))
    text = text.rstrip(', \n\r\t') + closing
    return text


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
- Keep each rule_text under 20 words to avoid token bloat.
- Keep each observation under 25 words.
- Keep encouragement under 30 words.

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
                max_output_tokens=65536,   # raised from 4096 — Critic JSON can be large
            ),
        )

        # ── 1. Best case: SDK already parsed into Pydantic ────────────
        if response.parsed is not None:
            return response.parsed

        # ── 2. Check finish reason before trying to parse text ────────
        finish_reason = None
        if response.candidates:
            finish_reason = str(response.candidates[0].finish_reason)
            if "MAX_TOKENS" in finish_reason or "max_tokens" in finish_reason.lower():
                # Response was cut — attempt JSON repair before giving up
                print(f"⚠️  Critic response hit token limit (finish_reason={finish_reason}). Attempting JSON repair...")

        raw_text = response.text or ""

        if not raw_text:
            raise ValueError(
                f"Critic LLM returned an empty response. Finish reason: {finish_reason or 'unknown'}"
            )

        # ── 3. Try parsing as-is first ────────────────────────────────
        try:
            return CriticEvaluation.model_validate_json(raw_text)
        except Exception:
            pass

        # ── 4. Attempt to repair truncated JSON ───────────────────────
        try:
            repaired = _repair_truncated_json(raw_text)
            return CriticEvaluation.model_validate_json(repaired)
        except Exception:
            pass

        # ── 5. Last resort: extract whatever partial data we can ──────
        try:
            partial = json.loads(_repair_truncated_json(raw_text))
            return CriticEvaluation(
                performance_score=partial.get("performance_score", 50),
                observations=partial.get("observations", ["Evaluation was truncated."]),
                proposed_rules=[
                    PolicyRule(**r) for r in partial.get("proposed_rules", [])
                    if all(k in r for k in ("rule_id", "rule_text", "source_date"))
                ],
                encouragement=partial.get("encouragement", "Keep going!"),
            )
        except Exception as final_err:
            raise ValueError(
                f"Critic LLM response could not be parsed even after repair.\n"
                f"Finish reason: {finish_reason}\n"
                f"Parse error: {final_err}\n"
                f"Raw text (first 500 chars): {raw_text[:500]}"
            )
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from rl_models import PolicyRule, UserPolicy


class PolicyStore:
    """
    Persistent per-user policy store backed by a JSON file.
    Stores learned scheduling rules and supports merge/prune operations.
    """

    MIN_CONFIDENCE = 0.1
    ACTIVE_THRESHOLD = 0.3
    CONFIDENCE_BOOST = 0.1
    CONFIDENCE_DECAY = 0.15

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.file_path = Path(f"policy_{user_id}.json")
        self.policy = self._load()

    def _load(self) -> UserPolicy:
        if self.file_path.exists():
            with open(self.file_path, "r") as f:
                data = json.load(f)
            return UserPolicy.model_validate(data)
        return UserPolicy(user_id=self.user_id)

    def _save(self) -> None:
        with open(self.file_path, "w") as f:
            json.dump(self.policy.model_dump(), f, indent=2, default=str)

    def get_all_rules(self) -> List[PolicyRule]:
        return list(self.policy.rules)

    def get_active_rules(self) -> List[PolicyRule]:
        return sorted(
            [r for r in self.policy.rules if r.confidence >= self.ACTIVE_THRESHOLD],
            key=lambda r: r.confidence,
            reverse=True,
        )

    def update_rules(self, proposed_rules: List[PolicyRule]) -> None:
        existing_map = {r.rule_id: r for r in self.policy.rules}

        for pr in proposed_rules:
            if pr.rule_id in existing_map:
                old = existing_map[pr.rule_id]
                old.rule_text = pr.rule_text
                old.confidence = min(1.0, old.confidence + self.CONFIDENCE_BOOST)
                old.source_date = pr.source_date
            else:
                existing_map[pr.rule_id] = pr

        self.policy.rules = [
            r for r in existing_map.values() if r.confidence >= self.MIN_CONFIDENCE
        ]
        self.policy.reflection_count += 1
        self.policy.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save()

    def get_policy_prompt_block(self) -> str:
        active = self.get_active_rules()
        if not active:
            return ""

        def _label(conf: float) -> str:
            if conf >= 0.7:
                return "HIGH"
            if conf >= 0.4:
                return "MEDIUM"
            return "LOW"

        lines = [
            f"- [{_label(r.confidence)} confidence] {r.rule_text}"
            for r in active
        ]
        return (
            "\n## Learned Scheduling Rules (from past self-reflections)\n"
            + "\n".join(lines)
            + "\n\nApply these rules when generating today's schedule. "
            "If a rule conflicts with explicit user input, user input wins.\n"
        )

    def to_dict(self) -> dict:
        return self.policy.model_dump()
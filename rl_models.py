from pydantic import BaseModel, Field
from typing import List, Optional


class TaskCompletion(BaseModel):
    """Per-task completion feedback from the user."""
    task_name: str
    completed: bool = True
    actual_minutes: Optional[int] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5, description="1=easy, 5=very hard")
    skip_reason: Optional[str] = None


class CompletionLog(BaseModel):
    """Full day completion data submitted by the user."""
    user_id: str
    date: str                                      # YYYY-MM-DD
    tasks: List[TaskCompletion]
    overall_satisfaction: int = Field(..., ge=1, le=10, description="1=terrible, 10=perfect day")
    reflection: Optional[str] = None               # Free-text self-reflection


class PolicyRule(BaseModel):
    """A single learned scheduling rule derived by the Critic."""
    rule_id: str                                    # e.g. "rule_time_est_001"
    rule_text: str                                  # Human-readable rule
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    source_date: str                                # Date the rule was first proposed
    category: str = Field(
        "general",
        description="time_estimation | energy_management | task_priority | attendance | general",
    )


class CriticEvaluation(BaseModel):
    """Output of the Critic's reflection on a single day."""
    performance_score: int = Field(..., ge=0, le=100)
    observations: List[str]                         # Textual insights
    proposed_rules: List[PolicyRule]                 # New / updated rules
    encouragement: str = ""                         # Motivational note


class UserPolicy(BaseModel):
    """Full policy container for a user — persisted to disk."""
    user_id: str
    rules: List[PolicyRule] = []
    last_updated: Optional[str] = None
    reflection_count: int = 0
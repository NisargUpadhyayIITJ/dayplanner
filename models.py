from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ── Scheduled Task (internal plan) ──────────────────────────────────

class ScheduledTask(BaseModel):
    time_slot: str
    task_name: str
    is_attendance_safe: bool
    estimated_minutes: int


class RoutineMetadata(BaseModel):
    confidence_score: float
    energy_peak_utilized: bool


class DailyRoutine(BaseModel):
    date: str
    scheduled_tasks: List[ScheduledTask]
    metadata: RoutineMetadata


# ── Input Models ─────────────────────────────────────────────────────

class Personality(BaseModel):
    chronotype: str = Field(..., description="early_bird | night_owl")
    energy_peaks: List[str]          # e.g. ["06:00-11:00", "16:00-20:00"]
    distraction_triggers: List[str]
    focus_style: str


class TimetableSlot(BaseModel):
    start_time: str   # "09:00"
    end_time: str     # "10:00"
    subject: str
    code: str
    is_attendance_critical: bool = True


class Goal(BaseModel):
    id: str
    title: str
    priority: int = 1          # 1 = highest
    category: str              # academic | personal | health | club
    deadline: Optional[str] = None


class MiscCommitment(BaseModel):
    time: str
    description: str
    duration_min: int


class DailyInput(BaseModel):
    user_id: str
    current_date: str                           # YYYY-MM-DD
    current_day: str                            # Monday
    personality: Personality
    timetable: List[TimetableSlot]
    long_term_goals: List[Goal]
    short_term_goals: List[Goal]
    misc_commitments: List[MiscCommitment]
    apps_to_align_with_focus_timer: List[str] = Field(
        default_factory=list,
        description="Apps to block/align during deep-work focus sessions",
    )
    today_deadlines: Optional[List[Dict[str, Any]]] = None
    archetype: Optional[str] = Field(
        None,
        description="User archetype e.g. 'grinder', 'balanced', 'explorer'",
    )


# ── Output Models (new structured response) ──────────────────────────

class TimetableMeta(BaseModel):
    institution: str = "Unknown Institution"
    program: str = "Unknown Program"
    semester: str = "Unknown Semester"
    section: str = "Unknown Section"
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    )
    timezone: str = "Asia/Kolkata"
    confidence: float = 0.9


class SuggestedTimetableEntry(BaseModel):
    day: str
    start: str
    end: str
    subject: str
    code: str


class RoutineResponseData(BaseModel):
    meta: TimetableMeta
    suggested_timetable: List[SuggestedTimetableEntry]
    scheduled_tasks: List[ScheduledTask]       # The actual day's plan
    warnings: List[str] = Field(default_factory=list)


class RoutineResponse(BaseModel):
    """Top-level API response envelope."""
    success: bool = True
    data: RoutineResponseData
    message: str = "Timetable extracted and normalized successfully"


# ── Internal TimeBlock (kept for compatibility) ───────────────────────

class TimeBlock(BaseModel):
    start_time: str
    end_time: str
    activity: str
    category: str               # lecture | deep_work | goal_task | break | misc
    priority: int
    estimated_min: int
    goal_ids: List[str] = []
    notes: str = ""
    attend: Optional[bool] = None   # for lectures
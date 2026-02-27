from pydantic import BaseModel, Field
from typing import List, Dict, Optional

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
    current_date: str          # YYYY-MM-DD
    current_day: str           # Monday
    personality: Personality
    timetable: List[TimetableSlot]
    long_term_goals: List[Goal]
    short_term_goals: List[Goal]
    misc_commitments: List[MiscCommitment]
    today_deadlines: Optional[List[Dict]] = None

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

class DailyRoutine(BaseModel):
    date: str
    user_id: str
    daily_summary: str
    total_focus_hours: float
    attendance_plan: Dict[str, Any]   # attended, skipped, 75% impact
    schedule: List[TimeBlock]
    deep_focus_blocks: List[Dict[str, str]]
    recommended_skips: List[str]
    energy_forecast: Dict[str, str]
    rationale: str
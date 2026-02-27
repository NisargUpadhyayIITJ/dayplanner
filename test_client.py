import json
from google import genai
from models import DailyRoutine
import os

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) # Assumes GEMINI_API_KEY environment variable is set

example_input = {
    "user_id": "upadhyay_nisarg",
    "current_date": "2026-03-01",
    "current_day": "Sunday",
    "personality": {
        "chronotype": "early_bird",
        "energy_peaks": ["06:00-11:00", "16:00-20:00"],
        "distraction_triggers": ["instagram", "whatsapp", "youtube"],
        "focus_style": "deep_work_mornings"
    },
    "timetable": [
        {"start_time": "09:00", "end_time": "10:00", "subject": "Mathematics", "code": "MA101", "is_attendance_critical": True},
        {"start_time": "11:00", "end_time": "12:00", "subject": "Physics", "code": "PH102", "is_attendance_critical": False}
    ],
    "long_term_goals": [
        {"id": "lt1", "title": "Secure 8.5+ CGPA this semester", "priority": 1, "category": "academic", "deadline": "2026-05-20"}
    ],
    "short_term_goals": [
        {"id": "st1", "title": "Finish DSA LeetCode 50", "priority": 1, "category": "academic", "deadline": "2026-03-15"}
    ],
    "misc_commitments": [
        {"time": "17:00", "description": "GDSC weekly meet", "duration_min": 60}
    ],
    "today_deadlines": [{"title": "Physics assignment", "due": "23:59"}]
}

print("Generating routine via Gemini API...")
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[str(example_input)],
    config={
        'response_mime_type': 'application/json',
        'response_schema': DailyRoutine,
    }
)

print("\n--- Generated Routine ---")
print(json.dumps(response.parsed.model_dump(), indent=2))
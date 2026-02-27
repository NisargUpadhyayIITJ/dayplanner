import httpx
import json

from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",  # Dummy API key
    base_url="http://localhost:8001/v1",  # Default vLLM server URL
)

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

# response = httpx.post(
#     "http://localhost:8001/generate_daily_routine",
#     json=example_input,
#     timeout=120
# )

chat_completion = client.chat.completions.create(
    model="LocoreMind/LocoOperator-4B",  # Use the model name you served
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": str(example_input)}
    ]
)

print(chat_completion.choices[0].message.content)

# print("Status:", response.status_code)
# print(json.dumps(response.json(), indent=2))
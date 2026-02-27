import httpx
import json

BASE_URL = "http://localhost:8000"

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

def test_generate_routine():
    print(f"Testing POST {BASE_URL}/generate_daily_routine...")
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{BASE_URL}/generate_daily_routine",
                json=example_input
            )
            
            if response.status_code == 200:
                print("✅ /generate_daily_routine successful!")
                data = response.json()
                print("\nReceived routine from API:")
                print(f"  Summary: {data.get('daily_summary')}")
                print(f"  Focus Hours: {data.get('total_focus_hours')}")
                return True
            else:
                print(f"❌ Generate routine failed with status {response.status_code}")
                print(response.text)
                return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}. Is the server running with `uvicorn main:app --reload`?")
        return False

def test_log_completion():
    print(f"\nTesting POST {BASE_URL}/log_completion...")
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{BASE_URL}/log_completion",
                params={
                    "user_id": "upadhyay_nisarg",
                    "date": "2026-03-01"
                },
                json={"tasks_completed": 5, "efficiency": "80%"} # Mock completion body
            )
            
            if response.status_code == 200:
                print("✅ /log_completion successful!")
                print(response.json())
                return True
            else:
                print(f"❌ Log completion failed with status {response.status_code}")
                print(response.text)
                return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}.")
        return False

if __name__ == "__main__":
    print(f"Starting API End-to-End Tests against {BASE_URL}")
    print("-" * 50)
    
    routine_success = test_generate_routine()
    if routine_success:
        test_log_completion()
    
    print("-" * 50)
    print("Tests finished.")

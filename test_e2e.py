import httpx
import json

BASE_URL = "http://localhost:8002"

# ── New extended input ────────────────────────────────────────────────
example_input = {
    "user_id": "upadhyay_nisarg",
    "current_date": "2026-02-28",
    "current_day": "Saturday",
    "personality": {
        "chronotype": "early_bird",
        "energy_peaks": ["06:00-11:00", "16:00-20:00"],
        "distraction_triggers": ["instagram", "whatsapp", "youtube"],
        "focus_style": "deep_work_mornings"
    },
    "timetable": [
        {"start_time": "09:00", "end_time": "10:00", "subject": "Operating Systems", "code": "CS601", "is_attendance_critical": True},
        {"start_time": "10:00", "end_time": "11:00", "subject": "Computer Networks",  "code": "CS602", "is_attendance_critical": True},
        {"start_time": "11:15", "end_time": "12:15", "subject": "Machine Learning",   "code": "CS603", "is_attendance_critical": False}
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
    "apps_to_align_with_focus_timer": ["Instagram", "WhatsApp", "YouTube", "Reddit"],
    "today_deadlines": [],
    "archetype": "grinder"
}

# ── Completion data ────────────────────────────────────────────────────
example_completion = {
    "user_id": "upadhyay_nisarg",
    "date": "2026-02-28",
    "tasks": [
        {"task_name": "Operating Systems",  "completed": True,  "actual_minutes": 58,  "difficulty_rating": 3},
        {"task_name": "Computer Networks",  "completed": True,  "actual_minutes": 62,  "difficulty_rating": 4},
        {"task_name": "Machine Learning",   "completed": False, "actual_minutes": 0,   "skip_reason": "Felt low energy"},
        {"task_name": "DSA LeetCode",       "completed": True,  "actual_minutes": 95,  "difficulty_rating": 4},
        {"task_name": "GDSC weekly meet",   "completed": True,  "actual_minutes": 65,  "difficulty_rating": 2},
    ],
    "overall_satisfaction": 7,
    "reflection": "Skipped ML because I was tired after back-to-back lectures. DSA ran long again."
}


def test_generate_routine():
    """Step 1: Generate a daily routine (Actor) — new envelope expected."""
    print(f"🎬 Testing POST {BASE_URL}/generate_daily_routine...")
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(f"{BASE_URL}/generate_daily_routine", json=example_input)

        if response.status_code == 200:
            data = response.json()
            print("✅ /generate_daily_routine successful!")
            print(f"  success          : {data.get('success')}")
            print(f"  message          : {data.get('message')}")
            meta = data.get("data", {}).get("meta", {})
            print(f"  institution      : {meta.get('institution')}")
            print(f"  program          : {meta.get('program')}")
            print(f"  semester         : {meta.get('semester')}")
            print(f"  confidence       : {meta.get('confidence')}")
            tt = data.get("data", {}).get("suggested_timetable", [])
            print(f"  timetable entries: {len(tt)}")
            tasks = data.get("data", {}).get("scheduled_tasks", [])
            print(f"  scheduled_tasks  : {len(tasks)}")
            warnings = data.get("data", {}).get("warnings", [])
            if warnings:
                for w in warnings:
                    print(f"  ⚠️  {w}")
            return True
        else:
            print(f"❌ Generate routine failed with status {response.status_code}")
            print(response.text)
            return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}. Is the server running?")
        return False


def test_log_completion():
    """Step 2: Log task completion data."""
    print(f"\n📝 Testing POST {BASE_URL}/log_completion...")
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(f"{BASE_URL}/log_completion", json=example_completion)

        if response.status_code == 200:
            print("✅ /log_completion successful!")
            print(f"  Response: {response.json()}")
            return True
        else:
            print(f"❌ Log completion failed with status {response.status_code}")
            print(response.text)
            return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}.")
        return False


def test_trigger_reflection():
    """Step 3: Trigger the Critic to reflect on the day."""
    print(f"\n🧠 Testing POST {BASE_URL}/trigger_reflection...")
    try:
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{BASE_URL}/trigger_reflection",
                params={"user_id": "upadhyay_nisarg", "date": "2026-02-28"},
            )

        if response.status_code == 200:
            data = response.json()
            print("✅ /trigger_reflection successful!")
            print(f"  Performance Score: {data.get('performance_score')}")
            for obs in data.get("observations", []):
                print(f"    • {obs}")
            for rule in data.get("proposed_rules", []):
                print(f"    📌 [{rule['category']}] {rule['rule_text']} (conf={rule['confidence']})")
            return True
        else:
            print(f"❌ Trigger reflection failed with status {response.status_code}")
            print(response.text)
            return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}.")
        return False


def test_view_policy():
    """Step 4: Inspect the learned policy."""
    print(f"\n📜 Testing GET {BASE_URL}/view_policy/upadhyay_nisarg...")
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(f"{BASE_URL}/view_policy/upadhyay_nisarg")

        if response.status_code == 200:
            data = response.json()
            print("✅ /view_policy successful!")
            print(f"  User      : {data.get('user_id')}")
            print(f"  Rules     : {len(data.get('rules', []))}")
            print(f"  Reflections: {data.get('reflection_count')}")
            for rule in data.get("rules", []):
                print(f"    📌 [{rule['category']}] {rule['rule_text']} (conf={rule['confidence']})")
            return True
        else:
            print(f"❌ View policy failed with status {response.status_code}")
            print(response.text)
            return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}.")
        return False


def test_full_loop():
    """Step 5: Generate a second routine — should use the learned policy."""
    print(f"\n🔄 Testing FULL LOOP: generating next-day routine WITH learned policy...")
    try:
        next_day_input = {
            **example_input,
            "current_date": "2026-03-01",
            "current_day": "Sunday",
        }
        with httpx.Client(timeout=120) as client:
            response = client.post(f"{BASE_URL}/generate_daily_routine", json=next_day_input)

        if response.status_code == 200:
            data = response.json()
            print("✅ Second /generate_daily_routine (with policy) successful!")
            print(f"  success: {data.get('success')}")
            print(f"  date   : {data.get('data', {}).get('meta', {}).get('generated_at')}")
            print(f"  tasks  : {len(data.get('data', {}).get('scheduled_tasks', []))}")
            return True
        else:
            print(f"❌ Second generate routine failed with status {response.status_code}")
            print(response.text)
            return False
    except httpx.ConnectError:
        print(f"❌ Failed to connect to {BASE_URL}.")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("ChronoForge — Actor-Critic RL Loop E2E Tests")
    print("=" * 60)

    steps = [
        ("1. Generate routine (Actor)", test_generate_routine),
        ("2. Log completion",           test_log_completion),
        ("3. Trigger reflection (Critic)", test_trigger_reflection),
        ("4. View learned policy",      test_view_policy),
        ("5. Generate routine with policy (Full Loop)", test_full_loop),
    ]

    for name, test_fn in steps:
        print(f"\n{'─' * 60}")
        print(f"STEP: {name}")
        print(f"{'─' * 60}")
        if not test_fn():
            print(f"\n⛔ Stopping — step '{name}' failed.")
            break

    print(f"\n{'=' * 60}")
    print("Tests finished.")
    print(f"{'=' * 60}")
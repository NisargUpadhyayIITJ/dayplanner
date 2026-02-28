"""
schedule_fixer.py
-----------------
Pure-logic post-processing for ChronoForge scheduled_tasks.

Responsibilities:
  1. Convert today's timetable entries into fixed CLASS tasks.
     The input timetable is the full WEEKLY timetable — multiple subjects
     can share the same time slot because they fall on different weekdays.
     We resolve this by keeping the FIRST subject seen per time window
     (one class slot per occupied interval).
  2. Merge CLASS tasks with the LLM-generated personal tasks.
  3. Detect and resolve ALL time-slot collisions:
       - CLASS tasks are immovable anchors.
       - Personal tasks are trimmed / split / dropped to fit the free windows.
  4. Return a clean, chronologically-ordered, collision-free list.

No LLM calls — deterministic logic only.
"""

from __future__ import annotations

from typing import List, Tuple, Dict

try:
    from models import ScheduledTask
except ImportError:
    pass  # ScheduledTask injected at runtime (tests / standalone use)


# ── time helpers ──────────────────────────────────────────────────────────────

def _to_minutes(t: str) -> int:
    """'HH:MM' -> total minutes since midnight."""
    h, m = t.strip().split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(minutes: int) -> str:
    """Total minutes -> 'HH:MM'  (supports post-midnight values >= 1440)."""
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def _parse_slot(time_slot: str) -> Tuple[int, int]:
    """'HH:MM-HH:MM' -> (start_minutes, end_minutes).
    Handles overnight slots e.g. '22:00-02:00' -> (1320, 1560)."""
    start_str, end_str = time_slot.split("-")
    start = _to_minutes(start_str)
    end   = _to_minutes(end_str)
    if end <= start:          # overnight
        end += 24 * 60
    return start, end


def _make_slot(start: int, end: int) -> str:
    return f"{_to_hhmm(start)}-{_to_hhmm(end)}"


def _overlaps(s1: int, e1: int, s2: int, e2: int) -> bool:
    return s1 < e2 and s2 < e1


# ── interval arithmetic ───────────────────────────────────────────────────────

def _subtract_intervals(
    start: int,
    end: int,
    blocked: List[Tuple[int, int]],
) -> List[Tuple[int, int]]:
    """Return free sub-windows inside [start, end] after removing all blocked intervals."""
    free: List[Tuple[int, int]] = [(start, end)]
    for b_start, b_end in blocked:
        new_free: List[Tuple[int, int]] = []
        for f_start, f_end in free:
            if b_end <= f_start or b_start >= f_end:      # no overlap
                new_free.append((f_start, f_end))
            else:
                if f_start < b_start:                      # left portion
                    new_free.append((f_start, b_start))
                if b_end < f_end:                          # right portion
                    new_free.append((b_end, f_end))
        free = new_free
    return free


# ── residual-overlap safety pass ─────────────────────────────────────────────

def _resolve_residual_overlaps(tasks: List[ScheduledTask]) -> List[ScheduledTask]:
    """
    Final safety sweep over a sorted task list.
    If two consecutive tasks still overlap:
      - CLASS always wins.
      - Personal task is pushed / trimmed.
    """
    if not tasks:
        return tasks

    result: List[ScheduledTask] = [tasks[0]]

    for task in tasks[1:]:
        prev     = result[-1]
        prev_end = _parse_slot(prev.time_slot)[1]
        t_start, t_end = _parse_slot(task.time_slot)

        if t_start >= prev_end:
            result.append(task)
            continue

        # ── collision ──
        if task.task_name.startswith("[CLASS]"):
            # Incoming CLASS wins -- trim the previous personal task if possible
            if not prev.task_name.startswith("[CLASS]"):
                prev_start = _parse_slot(prev.time_slot)[0]
                if prev_start < t_start:
                    result[-1] = ScheduledTask(
                        time_slot=_make_slot(prev_start, t_start),
                        task_name=prev.task_name,
                        is_attendance_safe=prev.is_attendance_safe,
                        estimated_minutes=t_start - prev_start,
                    )
                else:
                    result.pop()   # no space left -- drop the personal task entirely
            # CLASS-vs-CLASS overlap should not occur after step 2; skip silently
            result.append(task)
        else:
            # Personal task loses -- push start to prev_end
            new_duration = t_end - prev_end
            if new_duration > 0:
                result.append(ScheduledTask(
                    time_slot=_make_slot(prev_end, t_end),
                    task_name=task.task_name,
                    is_attendance_safe=task.is_attendance_safe,
                    estimated_minutes=new_duration,
                ))
            # else zero/negative duration -- drop silently

    return result


# ── main public function ──────────────────────────────────────────────────────

def build_collision_free_schedule(
    llm_tasks: List[ScheduledTask],
    timetable_entries: list,
) -> List[ScheduledTask]:
    """
    Parameters
    ----------
    llm_tasks         : scheduled_tasks returned by the LLM (may have collisions /
                        missing classes).
    timetable_entries : input_data.timetable -- the full weekly timetable as a flat
                        list of TimetableSlot objects or plain dicts.

    Returns
    -------
    A collision-free, chronologically-ordered List[ScheduledTask] that:
      * contains every unique class as a [CLASS] anchor task, and
      * fits all personal tasks from the LLM into the remaining free windows.
    """

    # ── Step 1: parse timetable entries into candidate class dicts ────────────
    # Deduplicate exact (start, end, subject) triples first.
    seen_exact: set = set()
    candidates: List[Dict] = []

    for entry in timetable_entries:
        e = entry.model_dump() if hasattr(entry, "model_dump") else dict(entry)

        start_str = e.get("start_time", "").strip()
        end_str   = e.get("end_time",   "").strip()
        subject   = e.get("subject",    "Class")
        critical  = bool(e.get("is_attendance_critical", False))

        if not start_str or not end_str:
            continue

        key = (start_str, end_str, subject)
        if key in seen_exact:
            continue
        seen_exact.add(key)

        start_m = _to_minutes(start_str)
        end_m   = _to_minutes(end_str)
        if end_m <= start_m:
            end_m += 24 * 60

        candidates.append({
            "start_m":  start_m,
            "end_m":    end_m,
            "subject":  subject,
            "critical": critical,
        })

    # Sort by start time so earlier entries win slot conflicts
    candidates.sort(key=lambda c: c["start_m"])

    # ── Step 2: assign one class per occupied time window ─────────────────────
    # The full weekly timetable can have multiple subjects at the same time
    # (they belong to different weekdays).  We keep the first subject seen for
    # each distinct interval; later subjects that overlap are skipped.
    class_tasks: List[ScheduledTask] = []
    accepted_intervals: List[Tuple[int, int]] = []

    for c in candidates:
        s, e = c["start_m"], c["end_m"]
        if any(_overlaps(s, e, os, oe) for os, oe in accepted_intervals):
            continue   # another class already owns this window
        accepted_intervals.append((s, e))
        class_tasks.append(ScheduledTask(
            time_slot=_make_slot(s, e),
            task_name=f"[CLASS] {c['subject']}",
            is_attendance_safe=not c["critical"],
            estimated_minutes=e - s,
        ))

    class_tasks.sort(key=lambda t: _parse_slot(t.time_slot)[0])
    fixed_intervals: List[Tuple[int, int]] = [_parse_slot(ct.time_slot) for ct in class_tasks]

    # ── Step 3: strip any [CLASS] tasks the LLM hallucinated ─────────────────
    personal_tasks = [t for t in llm_tasks if not t.task_name.startswith("[CLASS]")]

    # ── Step 4: carve personal tasks into the free windows ───────────────────
    fitted_personal: List[ScheduledTask] = []

    for task in personal_tasks:
        try:
            t_start, t_end = _parse_slot(task.time_slot)
        except Exception:
            continue  # skip malformed slots

        free_windows = _subtract_intervals(t_start, t_end, fixed_intervals)
        for w_start, w_end in free_windows:
            duration = w_end - w_start
            if duration <= 0:
                continue
            fitted_personal.append(ScheduledTask(
                time_slot=_make_slot(w_start, w_end),
                task_name=task.task_name,
                is_attendance_safe=task.is_attendance_safe,
                estimated_minutes=duration,
            ))

    # ── Step 5: merge, sort, final safety pass ────────────────────────────────
    merged = class_tasks + fitted_personal
    merged.sort(key=lambda t: _parse_slot(t.time_slot)[0])
    merged = _resolve_residual_overlaps(merged)

    return merged
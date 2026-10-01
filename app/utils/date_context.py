import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger("fitbuddy.date_context")

APP_TIMEZONE_STR = "Asia/Kolkata"
APP_TIMEZONE = ZoneInfo(APP_TIMEZONE_STR)

WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

def get_current_app_datetime() -> datetime:
    """
    Returns the authoritative application datetime in the configured timezone (Asia/Kolkata).
    Supports APP_TEST_DATE environment variable for deterministic development and automated testing.
    """
    test_date_env = os.getenv("APP_TEST_DATE")
    if test_date_env:
        try:
            test_date_env = test_date_env.strip()
            if " " in test_date_env or "T" in test_date_env:
                clean_str = test_date_env.replace("T", " ")
                dt = datetime.strptime(clean_str[:19], "%Y-%m-%d %H:%M:%S")
            else:
                dt = datetime.strptime(test_date_env[:10], "%Y-%m-%d")
            return dt.replace(tzinfo=APP_TIMEZONE)
        except Exception as e:
            logger.warning(f"Failed to parse APP_TEST_DATE='{test_date_env}': {e}. Using current real-time clock.")

    return datetime.now(APP_TIMEZONE)

def get_current_app_date() -> date:
    """Returns authoritative current application date."""
    return get_current_app_datetime().date()

def format_date_long(target_date: Optional[date] = None) -> str:
    """Formats date as 'October 2, 2026'."""
    d = target_date or get_current_app_date()
    return d.strftime("%B %-d, %Y") if hasattr(d, "strftime") else str(d)

def resolve_plan_day(
    days_data: List[Dict[str, Any]],
    target_date: Optional[date] = None
) -> Tuple[int, str, Optional[Dict[str, Any]]]:
    """
    Given a user's 7-day workout plan days and a target calendar date,
    determines the exact day number (1-7), weekday name, and matching day dictionary.
    """
    if not days_data:
        d = target_date or get_current_app_date()
        w_idx = d.weekday()
        return (w_idx + 1, WEEKDAY_NAMES[w_idx], None)

    d = target_date or get_current_app_date()
    weekday_idx = d.weekday()  # 0=Monday, ..., 4=Friday, 6=Sunday
    weekday_name = WEEKDAY_NAMES[weekday_idx]
    expected_day_number = weekday_idx + 1

    # 1. Match by day_number == expected_day_number (1=Monday, 2=Tuesday, ..., 5=Friday, 7=Sunday)
    for day in days_data:
        if isinstance(day, dict) and day.get("day_number") == expected_day_number:
            return (expected_day_number, weekday_name, day)

    # 2. Match by day_name containing weekday name
    for day in days_data:
        if isinstance(day, dict):
            d_name = day.get("day_name", "").strip().lower()
            if weekday_name.lower() in d_name:
                return (day.get("day_number", expected_day_number), weekday_name, day)

    # 3. Fallback: Array index modulo length
    idx = weekday_idx % len(days_data)
    fallback_day = days_data[idx] if isinstance(days_data[idx], dict) else None
    return (expected_day_number, weekday_name, fallback_day)

def resolve_day_by_weekday_name(
    days_data: List[Dict[str, Any]],
    target_weekday_name: str
) -> Tuple[int, str, Optional[Dict[str, Any]]]:
    """
    Finds a specific day from the plan by weekday name (e.g. 'Monday', 'Friday').
    """
    clean_target = target_weekday_name.strip().lower()
    for idx, name in enumerate(WEEKDAY_NAMES):
        if name.lower() == clean_target or clean_target in name.lower():
            target_num = idx + 1
            # Search in days_data
            for day in days_data:
                if isinstance(day, dict):
                    if name.lower() in day.get("day_name", "").lower() or day.get("day_number") == target_num:
                        return (day.get("day_number", target_num), name, day)
            # If not found directly, try index
            if 0 <= idx < len(days_data):
                return (target_num, name, days_data[idx])
            return (target_num, name, None)

    return (1, "Monday", days_data[0] if days_data else None)

def resolve_query_target_day(
    query: str,
    days_data: List[Dict[str, Any]],
    current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Parses user query for temporal intent (today, tomorrow, yesterday, Monday-Sunday, next workout)
    and resolves the exact target date, target day number, target weekday name, and day plan dict.
    """
    cur_date = current_date or get_current_app_date()
    query_lower = query.lower().strip()
    
    # 1. Tomorrow
    if any(term in query_lower for term in ["tomorrow", "tomorrow's", "tomorrows", "next day"]):
        target_date = cur_date + timedelta(days=1)
        day_num, weekday_name, day_dict = resolve_plan_day(days_data, target_date)
        return {
            "intent_type": "tomorrow",
            "target_date": target_date,
            "target_date_str": target_date.strftime("%Y-%m-%d"),
            "target_date_formatted": format_date_long(target_date),
            "target_weekday": weekday_name,
            "target_day_number": day_num,
            "day_data": day_dict,
            "label": f"tomorrow ({weekday_name}, {target_date.strftime('%b %-d')})"
        }

    # 2. Yesterday
    if any(term in query_lower for term in ["yesterday", "yesterday's", "yesterdays", "previous day"]):
        target_date = cur_date - timedelta(days=1)
        day_num, weekday_name, day_dict = resolve_plan_day(days_data, target_date)
        return {
            "intent_type": "yesterday",
            "target_date": target_date,
            "target_date_str": target_date.strftime("%Y-%m-%d"),
            "target_date_formatted": format_date_long(target_date),
            "target_weekday": weekday_name,
            "target_day_number": day_num,
            "day_data": day_dict,
            "label": f"yesterday ({weekday_name}, {target_date.strftime('%b %-d')})"
        }

    # 3. Specific Weekday Mentions (e.g., "what was monday's workout", "what about sunday", "on friday")
    for name in WEEKDAY_NAMES:
        pattern = rf"\b{name.lower()}(?:'s|s)?\b"
        if re.search(pattern, query_lower):
            day_num, weekday_name, day_dict = resolve_day_by_weekday_name(days_data, name)
            # Calculate calendar date for this weekday in the current week
            days_diff = (day_num - 1) - cur_date.weekday()
            target_date = cur_date + timedelta(days=days_diff)
            return {
                "intent_type": "specific_weekday",
                "target_date": target_date,
                "target_date_str": target_date.strftime("%Y-%m-%d"),
                "target_date_formatted": format_date_long(target_date),
                "target_weekday": weekday_name,
                "target_day_number": day_num,
                "day_data": day_dict,
                "label": f"{weekday_name} (Day {day_num})"
            }

    # 4. Next Workout / Next Training Day
    if any(term in query_lower for term in ["next workout", "next training", "next session", "when do i train next"]):
        # Search forward from tomorrow
        for offset in range(1, 8):
            cand_date = cur_date + timedelta(days=offset)
            d_num, w_name, d_dict = resolve_plan_day(days_data, cand_date)
            if d_dict and not d_dict.get("is_rest_day"):
                return {
                    "intent_type": "next_workout",
                    "target_date": cand_date,
                    "target_date_str": cand_date.strftime("%Y-%m-%d"),
                    "target_date_formatted": format_date_long(cand_date),
                    "target_weekday": w_name,
                    "target_day_number": d_num,
                    "day_data": d_dict,
                    "label": f"next workout on {w_name} ({cand_date.strftime('%b %-d')})"
                }

    # 5. Next Rest Day
    if any(term in query_lower for term in ["next rest day", "next recovery", "when is my rest day", "when do i rest"]):
        for offset in range(0, 8):
            cand_date = cur_date + timedelta(days=offset)
            d_num, w_name, d_dict = resolve_plan_day(days_data, cand_date)
            if d_dict and d_dict.get("is_rest_day"):
                prefix = "today" if offset == 0 else ("tomorrow" if offset == 1 else f"this {w_name}")
                return {
                    "intent_type": "next_rest_day",
                    "target_date": cand_date,
                    "target_date_str": cand_date.strftime("%Y-%m-%d"),
                    "target_date_formatted": format_date_long(cand_date),
                    "target_weekday": w_name,
                    "target_day_number": d_num,
                    "day_data": d_dict,
                    "label": f"{prefix} ({w_name}, {cand_date.strftime('%b %-d')})"
                }

    # Default: Today
    day_num, weekday_name, day_dict = resolve_plan_day(days_data, cur_date)
    return {
        "intent_type": "today",
        "target_date": cur_date,
        "target_date_str": cur_date.strftime("%Y-%m-%d"),
        "target_date_formatted": format_date_long(cur_date),
        "target_weekday": weekday_name,
        "target_day_number": day_num,
        "day_data": day_dict,
        "label": f"today ({weekday_name}, {cur_date.strftime('%b %-d')})"
    }

def build_authoritative_chat_context(
    user_info: Dict[str, Any],
    active_plan_dict: Optional[Dict[str, Any]],
    nutrition_dict: Optional[Dict[str, Any]],
    completed_days_map: Optional[Dict[int, Any]] = None,
    current_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Builds the unified, single-source-of-truth backend context dictionary.
    """
    cur_date = current_date or get_current_app_date()
    cur_dt = get_current_app_datetime()
    weekday_idx = cur_date.weekday()
    current_weekday = WEEKDAY_NAMES[weekday_idx]
    current_day_number = weekday_idx + 1

    days_data = (active_plan_dict.get("days", []) if active_plan_dict else [])
    today_day_num, today_weekday_name, today_workout = resolve_plan_day(days_data, cur_date)

    weekly_schedule = []
    for d in days_data:
        if isinstance(d, dict):
            d_num = d.get("day_number", 1)
            d_name = d.get("day_name", f"Day {d_num}")
            weekly_schedule.append({
                "day_number": d_num,
                "day_name": d_name,
                "workout_title": d.get("workout_title", "Session"),
                "focus": d.get("focus", ""),
                "duration_minutes": d.get("duration_minutes", 45),
                "is_rest_day": bool(d.get("is_rest_day", False)),
                "is_completed": bool(completed_days_map and d_num in completed_days_map),
                "is_today": bool(d_num == today_day_num or current_weekday.lower() in d_name.lower())
            })

    return {
        "current_date": cur_date.strftime("%Y-%m-%d"),
        "current_date_formatted": format_date_long(cur_date),
        "current_time": cur_dt.strftime("%H:%M"),
        "current_weekday": current_weekday,
        "current_day_number": current_day_number,
        "timezone": APP_TIMEZONE_STR,
        "user": user_info,
        "active_plan": active_plan_dict,
        "today_workout": today_workout,
        "today_day_number": today_day_num,
        "today_weekday": today_weekday_name,
        "today_is_rest_day": bool(today_workout.get("is_rest_day")) if today_workout else False,
        "weekly_schedule": weekly_schedule,
        "completed_days": list((completed_days_map or {}).keys()),
        "nutrition": nutrition_dict or {}
    }

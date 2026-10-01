import logging
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models.user import User
from app.models.workout_plan import WorkoutPlan
from app.models.daily_log import DailyWorkoutLog
from app.models.nutrition_tip import NutritionGuidance
from app.services.workout_service import workout_service
from app.services.nutrition_service import nutrition_service
from app.services.admin_service import admin_service
from app.utils.date_context import get_current_app_date, resolve_plan_day

logger = logging.getLogger("fitbuddy.views")
router = APIRouter(tags=["Views"])
templates = Jinja2Templates(directory="app/templates")

def get_current_user(db: Session, user_id: Optional[int] = None) -> Optional[User]:
    """Helper to fetch the current user or most recent active user."""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    # Fallback to the latest user or first user
    return db.query(User).order_by(desc(User.id)).first()

@router.get("/", response_class=HTMLResponse, summary="Landing Page")
def landing_page(request: Request, db: Session = Depends(get_db)):
    active_user = get_current_user(db)
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={"active_user": active_user, "user": active_user}
    )

@router.get("/onboard", response_class=HTMLResponse, summary="User Onboarding Wizard")
def onboarding_page(request: Request, db: Session = Depends(get_db)):
    active_user = get_current_user(db)
    return templates.TemplateResponse(
        request=request,
        name="onboarding.html",
        context={"active_user": active_user, "user": active_user}
    )

@router.get("/generating", response_class=HTMLResponse, summary="AI Generation Loading State")
def generation_page(
    request: Request,
    user_id: int = Query(...),
    plan_id: Optional[int] = Query(None),
    is_refinement: bool = Query(False),
    feedback: Optional[str] = Query(None),
    quick_tags: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(url="/onboard")
    
    return templates.TemplateResponse(
        request=request,
        name="generation.html",
        context={
            "user": user,
            "plan_id": plan_id,
            "is_refinement": is_refinement,
            "feedback": feedback or "",
            "quick_tags": quick_tags or ""
        }
    )

@router.get("/dashboard", response_class=HTMLResponse, summary="User Dashboard")
def dashboard_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    active_plan = workout_service.get_active_plan(db, user.id)
    if not active_plan:
        return RedirectResponse(url=f"/generating?user_id={user.id}")

    nutrition = nutrition_service.get_or_create_nutrition(db, user.id)
    logs = workout_service.get_plan_logs(db, active_plan.id)
    completed_days = {l.day_number: l for l in logs if l.completed}

    all_users = db.query(User).order_by(desc(User.id)).all()

    days_data = active_plan.days_data or []
    current_date = get_current_app_date()
    today_day_num, today_weekday, today_day = resolve_plan_day(days_data, current_date)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "active_plan": active_plan,
            "nutrition": nutrition,
            "completed_days": completed_days,
            "days_data": days_data,
            "today_day": today_day,
            "today_day_num": today_day_num,
            "today_weekday": today_weekday,
            "all_users": all_users,
            "page": "dashboard"
        }
    )

@router.get("/workout", response_class=HTMLResponse, summary="Weekly 7-Day Workout Plan")
def workout_plan_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    plan_id: Optional[int] = Query(None),
    active_day: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first() if plan_id else workout_service.get_active_plan(db, user.id)
    if not plan:
        return RedirectResponse(url=f"/generating?user_id={user.id}")

    logs = workout_service.get_plan_logs(db, plan.id)
    completed_days = {l.day_number: l for l in logs if l.completed}
    all_users = db.query(User).order_by(desc(User.id)).all()

    days_data = plan.days_data or []
    current_date = get_current_app_date()
    today_day_num, today_weekday, _ = resolve_plan_day(days_data, current_date)
    resolved_active_day = active_day if active_day is not None else today_day_num

    return templates.TemplateResponse(
        request=request,
        name="workout_plan.html",
        context={
            "user": user,
            "plan": plan,
            "days": days_data,
            "active_day": resolved_active_day,
            "today_day_num": today_day_num,
            "today_weekday": today_weekday,
            "completed_days": completed_days,
            "all_users": all_users,
            "page": "workout"
        }
    )

@router.get("/workout/day/{day_number}", response_class=HTMLResponse, summary="Daily Workout Focus & Tracker")
def daily_workout_page(
    request: Request,
    day_number: int,
    user_id: Optional[int] = Query(None),
    plan_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first() if plan_id else workout_service.get_active_plan(db, user.id)
    if not plan:
        return RedirectResponse(url="/dashboard")

    days_data = plan.days_data or []
    day_item = next((d for d in days_data if d.get("day_number") == day_number), None)
    if not day_item and days_data:
        day_item = days_data[0]
        day_number = 1

    log = db.query(DailyWorkoutLog).filter(
        DailyWorkoutLog.plan_id == plan.id,
        DailyWorkoutLog.user_id == user.id,
        DailyWorkoutLog.day_number == day_number
    ).first()

    cur_date = get_current_app_date()
    monday = cur_date - timedelta(days=cur_date.weekday())
    day_date = monday + timedelta(days=day_number - 1)
    day_date_formatted = day_date.strftime("%b %-d, %Y")

    all_users = db.query(User).order_by(desc(User.id)).all()

    return templates.TemplateResponse(
        request=request,
        name="daily_workout.html",
        context={
            "user": user,
            "plan": plan,
            "day": day_item,
            "day_number": day_number,
            "day_date_formatted": day_date_formatted,
            "log": log,
            "completed_exercises": log.completed_exercises if log else [],
            "all_users": all_users,
            "page": "daily_workout"
        }
    )

@router.get("/nutrition", response_class=HTMLResponse, summary="Nutrition & Recovery Module")
def nutrition_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    guidance = nutrition_service.get_or_create_nutrition(db, user.id)
    all_users = db.query(User).order_by(desc(User.id)).all()

    return templates.TemplateResponse(
        request=request,
        name="nutrition.html",
        context={
            "user": user,
            "nutrition": guidance,
            "all_users": all_users,
            "page": "nutrition"
        }
    )

@router.get("/refine", response_class=HTMLResponse, summary="Feedback & Plan Refinement")
def refine_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    plan_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first() if plan_id else workout_service.get_active_plan(db, user.id)
    if not plan:
        return RedirectResponse(url="/dashboard")

    all_users = db.query(User).order_by(desc(User.id)).all()

    return templates.TemplateResponse(
        request=request,
        name="refine_plan.html",
        context={
            "user": user,
            "plan": plan,
            "all_users": all_users,
            "page": "refine"
        }
    )

@router.get("/history", response_class=HTMLResponse, summary="Plan Version History")
def history_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    history = workout_service.get_plan_history(db, user.id)
    all_users = db.query(User).order_by(desc(User.id)).all()

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "user": user,
            "history": history,
            "all_users": all_users,
            "page": "history"
        }
    )

@router.get("/profile", response_class=HTMLResponse, summary="Profile Management")
def profile_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    plan_count = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).count()
    active_plan = workout_service.get_active_plan(db, user.id)
    all_users = db.query(User).order_by(desc(User.id)).all()

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "user": user,
            "plan_count": plan_count,
            "active_plan": active_plan,
            "all_users": all_users,
            "page": "profile"
        }
    )

@router.get("/chat", response_class=HTMLResponse, summary="AI Fitness Coach Chat Page")
def chat_page(
    request: Request,
    user_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(db, user_id)
    if not user:
        return RedirectResponse(url="/onboard")

    active_plan = workout_service.get_active_plan(db, user.id)
    nutrition = nutrition_service.get_or_create_nutrition(db, user.id)
    all_users = db.query(User).order_by(desc(User.id)).all()

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "user": user,
            "active_plan": active_plan,
            "nutrition": nutrition,
            "all_users": all_users,
            "page": "chat"
        }
    )

@router.get("/admin", response_class=HTMLResponse, summary="Admin Management Dashboard")
def admin_page(
    request: Request,
    db: Session = Depends(get_db)
):
    stats = admin_service.get_system_statistics(db)
    users = admin_service.list_admin_users(db)
    active_user = get_current_user(db)

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "stats": stats,
            "users": users,
            "active_user": active_user,
            "user": active_user,
            "page": "admin"
        }
    )

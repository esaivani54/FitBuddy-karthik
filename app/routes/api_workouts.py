import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.workout_plan import WorkoutPlan
from app.models.user import User
from app.schemas.workout import (
    WorkoutPlanCreateRequest, FeedbackRegenerateRequest,
    WorkoutPlanResponse, DailyLogCreateRequest
)
from app.services.workout_service import workout_service

logger = logging.getLogger("fitbuddy.api_workouts")
router = APIRouter(prefix="/api/workouts", tags=["Workouts"])

@router.post("/generate", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED, summary="Generate personalized 7-day workout plan")
def generate_workout(req: WorkoutPlanCreateRequest, db: Session = Depends(get_db)):
    """Triggers AI workout plan generation using user profile."""
    try:
        plan = workout_service.create_initial_plan(db, req.user_id)
        return plan
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Workout generation error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate workout plan: {str(e)}")

@router.get("/{plan_id}", response_model=WorkoutPlanResponse, summary="Get workout plan by ID")
def get_workout(plan_id: int, db: Session = Depends(get_db)):
    plan = workout_service.get_plan_by_id(db, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Workout plan with ID {plan_id} not found")
    return plan

@router.get("/user/{user_id}/active", response_model=WorkoutPlanResponse, summary="Get active workout plan for user")
def get_active_workout(user_id: int, db: Session = Depends(get_db)):
    plan = workout_service.get_active_plan(db, user_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No workout plan found for user ID {user_id}")
    return plan

@router.post("/feedback", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED, summary="Regenerate plan based on user feedback")
def refine_workout(req: FeedbackRegenerateRequest, db: Session = Depends(get_db)):
    """Incorporates user feedback into existing plan constraints and generates an updated version."""
    try:
        new_plan = workout_service.regenerate_plan(
            db=db,
            user_id=req.user_id,
            plan_id=req.plan_id,
            feedback=req.feedback,
            quick_tags=req.quick_tags
        )
        return new_plan
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Workout regeneration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to regenerate workout plan: {str(e)}")

@router.post("/activate/{plan_id}", response_model=WorkoutPlanResponse, summary="Set plan version as active")
def activate_plan(plan_id: int, user_id: int, db: Session = Depends(get_db)):
    try:
        plan = workout_service.set_active_version(db, user_id, plan_id)
        return plan
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))

@router.get("/user/{user_id}/history", response_model=List[WorkoutPlanResponse], summary="Get plan version history for user")
def get_history(user_id: int, db: Session = Depends(get_db)):
    return workout_service.get_plan_history(db, user_id)

@router.post("/log-day", summary="Log day completion")
def log_day_workout(log_req: DailyLogCreateRequest, db: Session = Depends(get_db)):
    log = workout_service.log_day_completion(
        db=db,
        plan_id=log_req.plan_id,
        user_id=log_req.user_id,
        day_number=log_req.day_number,
        completed=log_req.completed,
        completed_exercises=log_req.completed_exercises,
        duration_minutes=log_req.duration_minutes or 45,
        notes=log_req.notes
    )
    return {"status": "success", "day_number": log.day_number, "completed": log.completed, "logged_at": log.logged_at}

@router.get("/{plan_id}/logs", summary="Get completion logs for a plan")
def get_plan_logs(plan_id: int, db: Session = Depends(get_db)):
    logs = workout_service.get_plan_logs(db, plan_id)
    return [{"day_number": l.day_number, "completed": l.completed, "completed_exercises": l.completed_exercises, "notes": l.notes} for l in logs]

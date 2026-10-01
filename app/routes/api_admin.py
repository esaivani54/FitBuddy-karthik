import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.admin import AdminStatsResponse, AdminUserItem
from app.services.admin_service import admin_service
from app.models.user import User
from app.models.workout_plan import WorkoutPlan
from app.models.daily_log import DailyWorkoutLog
from app.models.nutrition_tip import NutritionGuidance

logger = logging.getLogger("fitbuddy.api_admin")
router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/statistics", response_model=AdminStatsResponse, summary="Get high-level system analytics")
def get_stats(db: Session = Depends(get_db)):
    return admin_service.get_system_statistics(db)

@router.get("/users", response_model=List[AdminUserItem], summary="Get list of all users with plan counts and metrics")
def get_admin_users(db: Session = Depends(get_db)):
    return admin_service.list_admin_users(db)

@router.post("/seed", summary="Seed sample users, plans, and completion logs")
def seed_demo_data(db: Session = Depends(get_db)):
    return {"status": "info", "message": "Manual seeding disabled. Users onboard directly."}

@router.post("/reset", summary="Reset all application data for clean slate testing")
def reset_all_data(db: Session = Depends(get_db)):
    db.query(DailyWorkoutLog).delete()
    db.query(NutritionGuidance).delete()
    db.query(WorkoutPlan).delete()
    db.query(User).delete()
    db.commit()
    return {"status": "success", "message": "Database reset cleanly to empty state."}

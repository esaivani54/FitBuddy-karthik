import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.models.user import User
from app.models.workout_plan import WorkoutPlan
from app.models.daily_log import DailyWorkoutLog
from app.models.nutrition_tip import NutritionGuidance
from app.services.workout_service import workout_service
from app.services.nutrition_service import nutrition_service

logger = logging.getLogger("fitbuddy.admin_service")

class AdminService:
    def get_system_statistics(self, db: Session) -> Dict[str, Any]:
        total_users = db.query(func.count(User.id)).scalar() or 0
        total_plans = db.query(func.count(WorkoutPlan.id)).scalar() or 0
        
        # Count plans with version > 1 as regenerations
        total_regenerations = db.query(func.count(WorkoutPlan.id)).filter(WorkoutPlan.version > 1).scalar() or 0
        completed_workouts = db.query(func.count(DailyWorkoutLog.id)).filter(DailyWorkoutLog.completed == True).scalar() or 0

        # Goal distribution
        goal_rows = db.query(User.goal, func.count(User.id)).group_by(User.goal).all()
        goal_distribution = {row[0]: row[1] for row in goal_rows}

        # Intensity distribution
        intensity_rows = db.query(User.intensity, func.count(User.id)).group_by(User.intensity).all()
        intensity_distribution = {row[0]: row[1] for row in intensity_rows}

        # Recent activity logs
        recent_plans = db.query(WorkoutPlan).order_by(desc(WorkoutPlan.created_at)).limit(8).all()
        recent_activity = []
        for p in recent_plans:
            u = db.query(User).filter(User.id == p.user_id).first()
            recent_activity.append({
                "plan_id": p.id,
                "user_id": p.user_id,
                "user_name": u.name if u else f"User #{p.user_id}",
                "version": p.version,
                "plan_title": p.plan_title,
                "goal": p.target_goal,
                "intensity": p.intensity,
                "feedback": p.feedback,
                "created_at": p.created_at.strftime("%b %d, %Y %H:%M")
            })

        return {
            "total_users": total_users,
            "total_plans": total_plans,
            "total_regenerations": total_regenerations,
            "completed_workouts": completed_workouts,
            "goal_distribution": goal_distribution,
            "intensity_distribution": intensity_distribution,
            "recent_activity": recent_activity
        }

    def list_admin_users(self, db: Session) -> List[Dict[str, Any]]:
        users = db.query(User).order_by(desc(User.created_at)).all()
        results = []
        for u in users:
            plan_count = db.query(func.count(WorkoutPlan.id)).filter(WorkoutPlan.user_id == u.id).scalar() or 0
            active_plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == u.id, WorkoutPlan.is_active == True).first()
            last_log = db.query(DailyWorkoutLog).filter(DailyWorkoutLog.user_id == u.id).order_by(desc(DailyWorkoutLog.logged_at)).first()
            
            results.append({
                "id": u.id,
                "name": u.name,
                "age": u.age,
                "weight": u.weight,
                "gender": u.gender,
                "height": u.height,
                "goal": u.goal,
                "intensity": u.intensity,
                "experience": u.experience,
                "plan_count": plan_count,
                "active_version": active_plan.version if active_plan else None,
                "active_plan_id": active_plan.id if active_plan else None,
                "last_active": last_log.logged_at.strftime("%b %d, %Y") if last_log else u.created_at.strftime("%b %d, %Y"),
                "created_at": u.created_at.strftime("%b %d, %Y")
            })
        return results

    def seed_sample_data(self, db: Session):
        """No hardcoded demo users. Users are created exclusively via user onboarding."""
        pass

admin_service = AdminService()

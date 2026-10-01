import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.user import User
from app.models.workout_plan import WorkoutPlan
from app.models.daily_log import DailyWorkoutLog
from app.services.ai_service import ai_service
from app.schemas.workout import WorkoutPlanDataSchema

logger = logging.getLogger("fitbuddy.workout_service")

class WorkoutService:
    def create_initial_plan(self, db: Session, user_id: int) -> WorkoutPlan:
        """Generates and saves the initial (v1) workout plan for a user."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Deactivate any previous plans if existing
        db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).update({"is_active": False})

        user_info = {
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "gender": user.gender,
            "height": user.height,
            "goal": user.goal,
            "intensity": user.intensity,
            "experience": user.experience,
            "equipment": user.equipment
        }

        # Generate via AI service
        plan_schema: WorkoutPlanDataSchema = ai_service.generate_workout_plan(user_info)

        plan = WorkoutPlan(
            user_id=user.id,
            version=1,
            plan_title=plan_schema.plan_title,
            summary=plan_schema.summary,
            target_goal=plan_schema.target_goal,
            intensity=plan_schema.intensity,
            days_data=plan_schema.model_dump()["days"],
            feedback=None,
            feedback_history=[],
            is_active=True
        )

        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    def regenerate_plan(self, db: Session, user_id: int, plan_id: int, feedback: str, quick_tags: Optional[List[str]] = None) -> WorkoutPlan:
        """Generates a new version (vN+1) of the workout plan incorporating user feedback."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        current_plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
        if not current_plan:
            raise ValueError(f"Workout plan with ID {plan_id} not found")

        # Determine next version
        latest_plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).order_by(desc(WorkoutPlan.version)).first()
        next_version = (latest_plan.version + 1) if latest_plan else 2

        user_info = {
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "experience": user.experience,
            "equipment": user.equipment
        }

        current_plan_info = {
            "plan_title": current_plan.plan_title,
            "summary": current_plan.summary,
            "target_goal": current_plan.target_goal,
            "intensity": current_plan.intensity,
            "days": current_plan.days_data
        }

        # Call AI regeneration
        plan_schema: WorkoutPlanDataSchema = ai_service.regenerate_workout_plan(
            user_info=user_info,
            current_plan=current_plan_info,
            feedback=feedback,
            quick_tags=quick_tags or []
        )

        # Build feedback history
        existing_history = list(current_plan.feedback_history or [])
        existing_history.append({
            "from_version": current_plan.version,
            "to_version": next_version,
            "feedback": feedback,
            "quick_tags": quick_tags or [],
            "created_at": str(current_plan.created_at)
        })

        # Deactivate all previous versions
        db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).update({"is_active": False})

        new_plan = WorkoutPlan(
            user_id=user.id,
            version=next_version,
            plan_title=plan_schema.plan_title,
            summary=plan_schema.summary,
            target_goal=plan_schema.target_goal,
            intensity=plan_schema.intensity,
            days_data=plan_schema.model_dump()["days"],
            feedback=feedback,
            feedback_history=existing_history,
            is_active=True
        )

        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return new_plan

    def get_active_plan(self, db: Session, user_id: int) -> Optional[WorkoutPlan]:
        """Fetches the active workout plan for the user, or latest if none marked active."""
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id, WorkoutPlan.is_active == True).first()
        if not plan:
            plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).order_by(desc(WorkoutPlan.version)).first()
        return plan

    def get_plan_by_id(self, db: Session, plan_id: int) -> Optional[WorkoutPlan]:
        return db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()

    def get_plan_history(self, db: Session, user_id: int) -> List[WorkoutPlan]:
        return db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).order_by(desc(WorkoutPlan.version)).all()

    def set_active_version(self, db: Session, user_id: int, plan_id: int) -> WorkoutPlan:
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id, WorkoutPlan.user_id == user_id).first()
        if not plan:
            raise ValueError("Plan not found for this user")
        
        db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).update({"is_active": False})
        plan.is_active = True
        db.commit()
        db.refresh(plan)
        return plan

    def swap_plan_days(
        self,
        db: Session,
        user_id: int,
        source_day_num: int,
        target_day_num: int,
        plan_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Swaps the workout schedules between two day numbers in the user's active workout plan.
        Genuinely updates the database (WorkoutPlan.days_data) and commits the change.
        """
        plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first() if plan_id else self.get_active_plan(db, user_id)
        if not plan or not plan.days_data:
            return None

        days_data = [dict(d) for d in plan.days_data if isinstance(d, dict)]
        idx_a = None
        idx_b = None

        for idx, d in enumerate(days_data):
            if d.get("day_number") == source_day_num:
                idx_a = idx
            if d.get("day_number") == target_day_num:
                idx_b = idx

        if idx_a is None or idx_b is None:
            if 1 <= source_day_num <= len(days_data) and 1 <= target_day_num <= len(days_data):
                idx_a = source_day_num - 1
                idx_b = target_day_num - 1
            else:
                return None

        day_a = dict(days_data[idx_a])
        day_b = dict(days_data[idx_b])

        # Swap fields while preserving day_number and day_name
        keys_to_swap = [
            "workout_title", "focus", "duration_minutes", "is_rest_day",
            "warmup", "exercises", "cooldown", "recovery_note"
        ]

        new_day_a = dict(day_a)
        new_day_b = dict(day_b)

        for k in keys_to_swap:
            new_day_a[k] = day_b.get(k)
            new_day_b[k] = day_a.get(k)

        days_data[idx_a] = new_day_a
        days_data[idx_b] = new_day_b

        # Record swap in feedback history
        from datetime import datetime
        history = list(plan.feedback_history or [])
        history.append({
            "action": "swap_days",
            "source_day": source_day_num,
            "target_day": target_day_num,
            "timestamp": datetime.utcnow().isoformat()
        })
        plan.feedback_history = history
        plan.days_data = days_data
        plan.updated_at = datetime.utcnow()

        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(plan, "days_data")
        flag_modified(plan, "feedback_history")

        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {
            "plan_id": plan.id,
            "plan_version": plan.version,
            "source_day_num": source_day_num,
            "source_day_name": new_day_a.get("day_name", f"Day {source_day_num}"),
            "source_new_title": new_day_a.get("workout_title"),
            "source_new_is_rest": new_day_a.get("is_rest_day", False),
            "source_new_focus": new_day_a.get("focus", ""),
            "target_day_num": target_day_num,
            "target_day_name": new_day_b.get("day_name", f"Day {target_day_num}"),
            "target_new_title": new_day_b.get("workout_title"),
            "target_new_is_rest": new_day_b.get("is_rest_day", False),
            "target_new_focus": new_day_b.get("focus", "")
        }

    def log_day_completion(
        self,
        db: Session,
        plan_id: int,
        user_id: int,
        day_number: int,
        completed: bool = True,
        completed_exercises: Optional[List[str]] = None,
        duration_minutes: int = 45,
        notes: Optional[str] = None
    ) -> DailyWorkoutLog:
        """Records or updates completion for a specific workout day."""
        log = db.query(DailyWorkoutLog).filter(
            DailyWorkoutLog.plan_id == plan_id,
            DailyWorkoutLog.user_id == user_id,
            DailyWorkoutLog.day_number == day_number
        ).first()

        if not log:
            log = DailyWorkoutLog(
                plan_id=plan_id,
                user_id=user_id,
                day_number=day_number,
                completed=completed,
                completed_exercises=completed_exercises or [],
                duration_minutes=duration_minutes,
                notes=notes
            )
            db.add(log)
        else:
            log.completed = completed
            log.completed_exercises = completed_exercises or []
            log.duration_minutes = duration_minutes
            if notes is not None:
                log.notes = notes

        db.commit()
        db.refresh(log)
        return log

    def get_plan_logs(self, db: Session, plan_id: int) -> List[DailyWorkoutLog]:
        return db.query(DailyWorkoutLog).filter(DailyWorkoutLog.plan_id == plan_id).all()

workout_service = WorkoutService()

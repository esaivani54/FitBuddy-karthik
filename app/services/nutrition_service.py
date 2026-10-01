import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.nutrition_tip import NutritionGuidance
from app.services.ai_service import ai_service
from app.schemas.nutrition import NutritionDataSchema

logger = logging.getLogger("fitbuddy.nutrition_service")

class NutritionService:
    def get_or_create_nutrition(self, db: Session, user_id: int) -> NutritionGuidance:
        """Retrieves active nutrition guidance for user or generates fresh goal-calibrated guidance."""
        existing = db.query(NutritionGuidance).filter(NutritionGuidance.user_id == user_id).first()
        if existing:
            return existing

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        user_info = {
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "gender": user.gender,
            "height": user.height
        }

        # Generate via AI service
        nutri_schema: NutritionDataSchema = ai_service.generate_nutrition_tip(user_info)

        guidance = NutritionGuidance(
            user_id=user.id,
            goal=nutri_schema.goal,
            calorie_estimate=nutri_schema.macro_split.calories_estimate,
            macro_split=nutri_schema.macro_split.model_dump(),
            daily_tips=nutri_schema.daily_tips.model_dump(),
            hydration_target=nutri_schema.hydration_target,
            recovery_protocols=nutri_schema.recovery_protocols,
            sleep_target=nutri_schema.sleep_target,
            disclaimer=nutri_schema.disclaimer
        )

        db.add(guidance)
        db.commit()
        db.refresh(guidance)
        return guidance

    def regenerate_nutrition(self, db: Session, user_id: int) -> NutritionGuidance:
        """Forces regeneration of nutrition guidance based on updated user goal or weight."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Delete previous guidance
        db.query(NutritionGuidance).filter(NutritionGuidance.user_id == user_id).delete()

        user_info = {
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "gender": user.gender,
            "height": user.height
        }

        nutri_schema: NutritionDataSchema = ai_service.generate_nutrition_tip(user_info)

        guidance = NutritionGuidance(
            user_id=user.id,
            goal=nutri_schema.goal,
            calorie_estimate=nutri_schema.macro_split.calories_estimate,
            macro_split=nutri_schema.macro_split.model_dump(),
            daily_tips=nutri_schema.daily_tips.model_dump(),
            hydration_target=nutri_schema.hydration_target,
            recovery_protocols=nutri_schema.recovery_protocols,
            sleep_target=nutri_schema.sleep_target,
            disclaimer=nutri_schema.disclaimer
        )

        db.add(guidance)
        db.commit()
        db.refresh(guidance)
        return guidance

nutrition_service = NutritionService()

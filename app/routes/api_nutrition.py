import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.nutrition_tip import NutritionGuidance
from app.schemas.nutrition import NutritionResponse, NutritionGenerateRequest
from app.services.nutrition_service import nutrition_service

logger = logging.getLogger("fitbuddy.api_nutrition")
router = APIRouter(prefix="/api/nutrition", tags=["Nutrition"])

@router.get("/{user_id}", response_model=NutritionResponse, summary="Get active nutrition guidance for user")
def get_nutrition(user_id: int, db: Session = Depends(get_db)):
    try:
        guidance = nutrition_service.get_or_create_nutrition(db, user_id)
        return guidance
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Nutrition retrieval error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch nutrition guidance")

@router.post("/{user_id}/regenerate", response_model=NutritionResponse, summary="Regenerate nutrition guidance")
def regenerate_nutrition(user_id: int, db: Session = Depends(get_db)):
    try:
        guidance = nutrition_service.regenerate_nutrition(db, user_id)
        return guidance
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Nutrition regeneration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to regenerate nutrition guidance")

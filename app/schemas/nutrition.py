from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class MacroSplitSchema(BaseModel):
    protein: str = Field(..., description="Protein recommendation (e.g. 150g / 30%)")
    carbohydrates: str = Field(..., description="Carbs recommendation (e.g. 200g / 40%)")
    fats: str = Field(..., description="Fats recommendation (e.g. 60g / 30%)")
    calories_estimate: str = Field(..., description="Daily caloric target (e.g. 2,100 - 2,300 kcal)")

class DailyTipsSchema(BaseModel):
    nutrition: str = Field(..., description="Actionable nutrition guideline for the goal")
    hydration: str = Field(..., description="Daily water & electrolyte protocol")
    recovery: str = Field(..., description="Musculoskeletal recovery and mobility advice")
    sleep: str = Field(..., description="Circadian and sleep optimization recommendation")

class NutritionDataSchema(BaseModel):
    goal: str
    macro_split: MacroSplitSchema
    daily_tips: DailyTipsSchema
    hydration_target: str
    recovery_protocols: List[str]
    sleep_target: str
    disclaimer: str

class NutritionGenerateRequest(BaseModel):
    user_id: int

class NutritionResponse(BaseModel):
    id: int
    user_id: int
    goal: str
    calorie_estimate: Optional[str] = None
    macro_split: Optional[Dict[str, Any]] = None
    daily_tips: Dict[str, Any]
    hydration_target: Optional[str] = None
    recovery_protocols: Optional[List[str]] = None
    sleep_target: Optional[str] = None
    disclaimer: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

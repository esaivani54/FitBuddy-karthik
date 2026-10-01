from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full Name")
    age: int = Field(..., ge=12, le=100, description="Age in years (12-100)")
    weight: float = Field(..., ge=25.0, le=350.0, description="Weight in kg (25-350)")
    gender: Optional[str] = Field(default="Not specified", max_length=50)
    height: Optional[float] = Field(default=175.0, ge=80.0, le=250.0, description="Height in cm")
    goal: str = Field(..., min_length=2, max_length=100, description="Primary Fitness Goal")
    intensity: str = Field(..., min_length=2, max_length=50, description="Workout Intensity: Low, Medium, High")
    experience: Optional[str] = Field(default="Intermediate", max_length=50)
    equipment: Optional[str] = Field(default="Full Gym", max_length=100)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        valid_goals = ["Weight Loss", "Muscle Gain", "General Wellness", "Endurance & Stamina", "Strength & Power", "Athletic Performance", "Flexibility & Mobility"]
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Goal cannot be empty")
        return cleaned

    @field_validator("intensity")
    @classmethod
    def validate_intensity(cls, v: str) -> str:
        valid_intensities = ["Low", "Medium", "High"]
        cleaned = v.strip().capitalize()
        if cleaned not in valid_intensities:
            # Allow case insensitive match or standard fallback
            for vi in valid_intensities:
                if vi.lower() == cleaned.lower():
                    return vi
            raise ValueError(f"Intensity must be one of: {', '.join(valid_intensities)}")
        return cleaned

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    age: Optional[int] = Field(None, ge=12, le=100)
    weight: Optional[float] = Field(None, ge=25.0, le=350.0)
    gender: Optional[str] = Field(None, max_length=50)
    height: Optional[float] = Field(None, ge=80.0, le=250.0)
    goal: Optional[str] = Field(None, min_length=2, max_length=100)
    intensity: Optional[str] = Field(None, min_length=2, max_length=50)
    experience: Optional[str] = Field(None, max_length=50)
    equipment: Optional[str] = Field(None, max_length=100)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

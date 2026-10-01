from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class WarmupItemSchema(BaseModel):
    exercise: str = Field(..., description="Warm-up movement")
    duration_or_reps: str = Field(..., description="Duration or repetitions (e.g. 5 min, 15 reps)")

class ExerciseSchema(BaseModel):
    name: str = Field(..., description="Exercise Name (e.g. Barbell Bench Press)")
    sets: int = Field(default=3, ge=1, le=10, description="Number of sets")
    reps: str = Field(default="10-12 reps", description="Repetition range or time (e.g. 8-10 reps, 45s)")
    rest: str = Field(default="60 sec", description="Rest period between sets")
    target_muscles: Optional[str] = Field(default="General", description="Primary muscle groups worked")
    tempo: Optional[str] = Field(default="2-0-2", description="Rep tempo (e.g. 2s down, 0 pause, 2s up)")
    notes: Optional[str] = Field(default="", description="Form cue or safety note")

class CooldownItemSchema(BaseModel):
    exercise: str = Field(..., description="Cooldown movement or stretch")
    duration_or_reps: str = Field(..., description="Duration or repetitions (e.g. 30s hold)")

class DayWorkoutSchema(BaseModel):
    day_number: int = Field(..., ge=1, le=7, description="Day of the week (1-7)")
    day_name: str = Field(..., description="Day name (e.g. Monday, Day 1)")
    workout_title: str = Field(..., description="Theme/Title of the workout")
    focus: str = Field(..., description="Primary focus area (e.g. Upper Body Strength, Active Recovery)")
    duration_minutes: int = Field(default=45, ge=10, le=180, description="Estimated duration in minutes")
    is_rest_day: bool = Field(default=False, description="Whether this day is a designated rest/recovery day")
    warmup: List[WarmupItemSchema] = Field(default_factory=list, description="Warm-up routine")
    exercises: List[ExerciseSchema] = Field(default_factory=list, description="Main resistance or cardio exercises")
    cooldown: List[CooldownItemSchema] = Field(default_factory=list, description="Cooldown and stretching")
    recovery_note: str = Field(default="Stay hydrated and prioritize sleep.", description="Specific recovery advice for today")

class WorkoutPlanDataSchema(BaseModel):
    plan_title: str = Field(..., description="Engaging title for the 7-day routine")
    summary: str = Field(..., description="Executive summary of the weekly strategy")
    target_goal: str = Field(..., description="Target fitness goal")
    intensity: str = Field(..., description="Intensity tier")
    days: List[DayWorkoutSchema] = Field(..., min_length=7, max_length=7, description="Structured 7-day schedule")

class WorkoutPlanCreateRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user to generate the plan for")

class FeedbackRegenerateRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user")
    plan_id: int = Field(..., description="ID of the workout plan being refined")
    feedback: str = Field(..., min_length=3, max_length=1000, description="User's specific refinement instructions")
    quick_tags: Optional[List[str]] = Field(default_factory=list, description="Selected quick modification tags")

class DailyLogCreateRequest(BaseModel):
    plan_id: int
    user_id: int
    day_number: int = Field(..., ge=1, le=7)
    completed: bool = True
    completed_exercises: List[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = 45
    notes: Optional[str] = None

class WorkoutPlanResponse(BaseModel):
    id: int
    user_id: int
    version: int
    plan_title: str
    summary: Optional[str]
    target_goal: str
    intensity: str
    days_data: Any
    feedback: Optional[str] = None
    feedback_history: Optional[List[Any]] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

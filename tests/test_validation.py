import pytest
from pydantic import ValidationError
from app.schemas.user import UserCreate
from app.schemas.workout import DayWorkoutSchema, ExerciseSchema, WorkoutPlanDataSchema

def test_valid_user_schema():
    user = UserCreate(
        name="Jordan Lee",
        age=29,
        weight=74.5,
        goal="Muscle Gain",
        intensity="High"
    )
    assert user.name == "Jordan Lee"
    assert user.age == 29
    assert user.weight == 74.5
    assert user.intensity == "High"

def test_invalid_age_validation():
    with pytest.raises(ValidationError):
        UserCreate(
            name="Too Young",
            age=10,  # Min is 12
            weight=50.0,
            goal="Weight Loss",
            intensity="Low"
        )
        
    with pytest.raises(ValidationError):
        UserCreate(
            name="Too Old",
            age=105,  # Max is 100
            weight=60.0,
            goal="Weight Loss",
            intensity="Low"
        )

def test_invalid_weight_validation():
    with pytest.raises(ValidationError):
        UserCreate(
            name="Underweight",
            age=25,
            weight=15.0,  # Min is 25.0 kg
            goal="Weight Loss",
            intensity="Low"
        )

def test_invalid_intensity_validation():
    with pytest.raises(ValidationError):
        UserCreate(
            name="Extreme Guy",
            age=25,
            weight=75.0,
            goal="Muscle Gain",
            intensity="Insane"  # Not Low/Medium/High
        )

def test_workout_plan_schema_requires_7_days():
    # Attempting to validate a plan with fewer than 7 days
    sample_day = DayWorkoutSchema(
        day_number=1,
        day_name="Monday",
        workout_title="Upper Power",
        focus="Chest",
        duration_minutes=45,
        is_rest_day=False,
        exercises=[
            ExerciseSchema(name="Bench Press", sets=3, reps="10 reps", rest="60s")
        ]
    )
    
    with pytest.raises(ValidationError):
        WorkoutPlanDataSchema(
            plan_title="Short Plan",
            summary="Incomplete",
            target_goal="Muscle Gain",
            intensity="High",
            days=[sample_day]  # Only 1 day provided, expects exactly 7
        )

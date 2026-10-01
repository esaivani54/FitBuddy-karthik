import pytest
from app.models.user import User
from app.models.workout_plan import WorkoutPlan
from app.models.nutrition_tip import NutritionGuidance

def test_database_persistence_and_relationships(db_session):
    # 1. Create User
    user = User(
        name="Arthur Curry",
        age=32,
        weight=85.0,
        goal="Endurance & Stamina",
        intensity="High"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.id is not None

    # 2. Add Workout Plan
    plan = WorkoutPlan(
        user_id=user.id,
        version=1,
        plan_title="Aquatic Endurance Split",
        target_goal="Endurance & Stamina",
        intensity="High",
        days_data=[{"day_number": 1, "workout_title": "Swim & Core"}]
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    # 3. Add Nutrition Guidance
    nutri = NutritionGuidance(
        user_id=user.id,
        goal="Endurance & Stamina",
        daily_tips={"nutrition": "Carb loading", "hydration": "4L", "recovery": "Ice bath", "sleep": "8h"}
    )
    db_session.add(nutri)
    db_session.commit()
    db_session.refresh(nutri)

    # 4. Verify Relationships
    reloaded_user = db_session.query(User).filter(User.id == user.id).first()
    assert len(reloaded_user.workout_plans) == 1
    assert reloaded_user.workout_plans[0].plan_title == "Aquatic Endurance Split"
    assert len(reloaded_user.nutrition_guidance) == 1

    # 5. Verify Cascade Deletion
    db_session.delete(reloaded_user)
    db_session.commit()
    assert db_session.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id).count() == 0
    assert db_session.query(NutritionGuidance).filter(NutritionGuidance.user_id == user.id).count() == 0

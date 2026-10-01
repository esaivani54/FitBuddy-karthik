import pytest

def test_generate_and_retrieve_workout(client):
    # 1. Create a user
    user_res = client.post("/api/users", json={
        "name": "Marcus Kane",
        "age": 30,
        "weight": 80.0,
        "goal": "Weight Loss",
        "intensity": "Medium"
    })
    user_id = user_res.json()["id"]

    # 2. Trigger Workout Generation
    gen_res = client.post("/api/workouts/generate", json={"user_id": user_id})
    assert gen_res.status_code == 201
    plan_data = gen_res.json()
    assert plan_data["version"] == 1
    assert plan_data["user_id"] == user_id
    
    # Check days length
    days = plan_data["days_data"] if isinstance(plan_data["days_data"], list) else plan_data["days_data"].get("days", [])
    assert len(days) == 7

    # 3. Retrieve Active Workout
    active_res = client.get(f"/api/workouts/user/{user_id}/active")
    assert active_res.status_code == 200
    assert active_res.json()["id"] == plan_data["id"]

def test_log_workout_day_completion(client):
    user_res = client.post("/api/users", json={
        "name": "Bruce Wayne",
        "age": 35,
        "weight": 90.0,
        "goal": "Strength & Power",
        "intensity": "High"
    })
    user_id = user_res.json()["id"]
    plan_res = client.post("/api/workouts/generate", json={"user_id": user_id})
    plan_id = plan_res.json()["id"]

    # Log Day 1 completion
    log_res = client.post("/api/workouts/log-day", json={
        "plan_id": plan_id,
        "user_id": user_id,
        "day_number": 1,
        "completed": True,
        "completed_exercises": ["Trap Bar Deadlift", "Overhead Press"],
        "duration_minutes": 50,
        "notes": "Excellent session, felt explosive."
    })
    assert log_res.status_code == 200
    assert log_res.json()["completed"] is True

    # Retrieve logs
    logs_res = client.get(f"/api/workouts/{plan_id}/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) >= 1
    assert logs[0]["day_number"] == 1
    assert logs[0]["completed"] is True

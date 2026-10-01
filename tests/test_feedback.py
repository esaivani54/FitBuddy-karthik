import pytest

def test_feedback_regeneration_and_versioning(client):
    # 1. Create user and initial plan (v1)
    user_res = client.post("/api/users", json={
        "name": "Diana Prince",
        "age": 28,
        "weight": 68.0,
        "goal": "Muscle Gain",
        "intensity": "Medium"
    })
    user_id = user_res.json()["id"]

    v1_res = client.post("/api/workouts/generate", json={"user_id": user_id})
    v1_data = v1_res.json()
    assert v1_data["version"] == 1
    v1_id = v1_data["id"]

    # 2. Submit Feedback to regenerate plan (v2)
    refine_res = client.post("/api/workouts/feedback", json={
        "user_id": user_id,
        "plan_id": v1_id,
        "feedback": "I need more upper body cardio and two full recovery days on weekends.",
        "quick_tags": ["More cardio / HIIT", "Add 2 rest & recovery days"]
    })
    assert refine_res.status_code == 201
    v2_data = refine_res.json()
    assert v2_data["version"] == 2
    assert v2_data["is_active"] is True
    assert "feedback" in v2_data

    # 3. Check History Timeline
    hist_res = client.get(f"/api/workouts/user/{user_id}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 2
    assert history[0]["version"] == 2
    assert history[1]["version"] == 1

    # 4. Switch back to v1
    switch_res = client.post(f"/api/workouts/activate/{v1_id}?user_id={user_id}")
    assert switch_res.status_code == 200
    assert switch_res.json()["id"] == v1_id
    assert switch_res.json()["is_active"] is True

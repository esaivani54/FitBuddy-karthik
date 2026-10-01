import pytest

def test_nutrition_generation_and_categories(client):
    user_res = client.post("/api/users", json={
        "name": "Clark Kent",
        "age": 30,
        "weight": 88.0,
        "goal": "Muscle Gain",
        "intensity": "High"
    })
    user_id = user_res.json()["id"]

    # Fetch/generate nutrition guidance
    nutri_res = client.get(f"/api/nutrition/{user_id}")
    assert nutri_res.status_code == 200
    data = nutri_res.json()
    assert data["goal"] == "Muscle Gain"
    assert "daily_tips" in data
    assert "nutrition" in data["daily_tips"]
    assert "hydration" in data["daily_tips"]
    assert "recovery" in data["daily_tips"]
    assert "sleep" in data["daily_tips"]
    assert data["hydration_target"] is not None
    assert data["disclaimer"] is not None

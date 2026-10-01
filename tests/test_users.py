import pytest

def test_create_and_retrieve_user(client):
    payload = {
        "name": "Sarah Connor",
        "age": 34,
        "weight": 62.5,
        "height": 170.0,
        "gender": "Female",
        "goal": "Endurance & Stamina",
        "intensity": "High",
        "experience": "Advanced",
        "equipment": "Full Gym"
    }

    # Create user
    response = client.post("/api/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sarah Connor"
    assert data["id"] is not None
    user_id = data["id"]

    # Retrieve user
    get_res = client.get(f"/api/users/{user_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Sarah Connor"
    assert get_res.json()["weight"] == 62.5

def test_update_user_profile(client):
    payload = {
        "name": "John Matrix",
        "age": 40,
        "weight": 95.0,
        "goal": "Muscle Gain",
        "intensity": "High"
    }
    create_res = client.post("/api/users", json=payload)
    user_id = create_res.json()["id"]

    # Update weight and goal
    update_payload = {"weight": 92.0, "goal": "Weight Loss"}
    put_res = client.put(f"/api/users/{user_id}", json=update_payload)
    assert put_res.status_code == 200
    assert put_res.json()["weight"] == 92.0
    assert put_res.json()["goal"] == "Weight Loss"

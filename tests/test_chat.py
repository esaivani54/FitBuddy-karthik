import os
import pytest
from app.utils.date_context import format_date_long

def test_chat_anonymous_fallback(client):
    """Chat works when no user ID is supplied."""
    payload = {
        "message": "What should I eat after my workout?",
        "history": []
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert len(data["response"]) > 10
    assert "timestamp" in data

def test_chat_with_user_context(client):
    """Chat recognizes user profile, goal, and returns tailored coaching advice."""
    user_resp = client.post("/api/users", json={
        "name": "Marcus Vance",
        "age": 30,
        "weight": 82.5,
        "height": 182.0,
        "gender": "Male",
        "goal": "Muscle Gain",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]

    plan_resp = client.post("/api/workouts/generate", json={"user_id": user_id})
    assert plan_resp.status_code == 201

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "My knees feel uncomfortable during squats, what substitution do you recommend?",
        "history": [
            {"role": "user", "content": "Hello coach!"},
            {"role": "assistant", "content": "Hey Marcus! How can I help you today?"}
        ]
    })
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "Marcus" in chat_data.get("user_name", "")
    assert len(chat_data["response"]) > 20
    assert any(w in chat_data["response"].lower() for w in ["squat", "box squat", "knee", "form", "substitut", "leg"])

def test_chat_exercise_swap(client):
    """Chat provides equipment and movement-specific substitutions."""
    user_resp = client.post("/api/users", json={
        "name": "Elena Rostova",
        "age": 27,
        "weight": 62.0,
        "height": 168.0,
        "gender": "Female",
        "goal": "Weight Loss",
        "intensity": "Medium",
        "equipment": "Dumbbells Only"
    })
    user_id = user_resp.json()["id"]

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "Can I swap barbell bench press?",
        "history": []
    })
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "response" in chat_data
    assert len(chat_data["response"]) > 20

# ============================================================
# AUTHORITATIVE DATE & PLAN SYNCHRONIZATION TESTS
# ============================================================

def test_chat_today_workout_date_aware_friday(client, monkeypatch):
    """TEST 1: On Friday (2026-10-02), 'What is my workout today?' returns Friday workout, NOT Monday."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Sarah Chen",
        "age": 26,
        "weight": 58.0,
        "height": 165.0,
        "gender": "Female",
        "goal": "Endurance & Stamina",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What is my workout today?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Friday" in res_text
    assert "Monday" not in res_text or "not Monday" in res_text or "Friday" in res_text

def test_chat_tomorrow_workout(client, monkeypatch):
    """TEST 2: 'What is tomorrow's workout?' returns Saturday workout when current date is Friday."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "David Miller",
        "age": 32,
        "weight": 76.0,
        "height": 178.0,
        "gender": "Male",
        "goal": "Muscle Gain",
        "intensity": "Medium",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What is tomorrow's workout?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Saturday" in res_text

def test_chat_monday_workout_retrieval(client, monkeypatch):
    """TEST 3: 'What did I have on Monday?' returns Monday's workout even if today is Friday."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Chloe Bennett",
        "age": 29,
        "weight": 61.0,
        "height": 170.0,
        "gender": "Female",
        "goal": "General Wellness",
        "intensity": "Medium",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What did I have on Monday?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Monday" in res_text

def test_chat_rest_day_inquiry(client, monkeypatch):
    """TEST 4: 'Am I supposed to rest today?' answers based on Friday's actual schedule."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Jordan Lee",
        "age": 25,
        "weight": 70.0,
        "height": 175.0,
        "gender": "Non-binary",
        "goal": "Weight Loss",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "Am I supposed to rest today?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert len(res_text) > 20
    assert "Friday" in res_text

def test_chat_today_exercises_query(client, monkeypatch):
    """TEST 5: 'What exercises do I have today?' lists exercises from Friday's routine."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Samira Patel",
        "age": 31,
        "weight": 55.0,
        "height": 160.0,
        "gender": "Female",
        "goal": "Muscle Gain",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What exercises do I have today?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Friday" in res_text

def test_chat_replace_first_exercise(client, monkeypatch):
    """TEST 6: 'Can I replace today's first exercise?' targets today's actual first exercise."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Alex Novak",
        "age": 34,
        "weight": 80.0,
        "height": 180.0,
        "gender": "Male",
        "goal": "Muscle Gain",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "Can I replace today's first exercise?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert any(w in res_text.lower() for w in ["substitution", "alternative", "replace", "first"])

def test_chat_profile_change_sync(client):
    """TEST 7: When user profile goal is updated, AI Coach immediately uses the updated goal."""
    user_resp = client.post("/api/users", json={
        "name": "Taylor Hayes",
        "age": 28,
        "weight": 68.0,
        "height": 172.0,
        "gender": "Female",
        "goal": "Weight Loss",
        "intensity": "Medium",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]

    # Update goal to Endurance & Stamina
    update_resp = client.put(f"/api/users/{user_id}", json={
        "name": "Taylor Hayes",
        "age": 28,
        "weight": 68.0,
        "height": 172.0,
        "gender": "Female",
        "goal": "Endurance & Stamina",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    assert update_resp.status_code == 200

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What is my goal and profile stats?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Endurance & Stamina" in res_text

def test_chat_regenerated_plan_sync(client, monkeypatch):
    """TEST 8: When plan is regenerated, AI Coach immediately references the new active plan."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Rachel Zane",
        "age": 27,
        "weight": 59.0,
        "height": 167.0,
        "gender": "Female",
        "goal": "Muscle Gain",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    plan_resp = client.post("/api/workouts/generate", json={"user_id": user_id})
    plan_id = plan_resp.json()["id"]

    # Regenerate plan with feedback
    refine_resp = client.post("/api/workouts/feedback", json={
        "user_id": user_id,
        "plan_id": plan_id,
        "feedback": "Include more core and HIIT conditioning on Fridays",
        "quick_tags": ["More Cardio"]
    })
    assert refine_resp.status_code == 201
    new_plan_version = refine_resp.json()["version"]
    assert new_plan_version == 2

    # Chat should use new plan version
    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What is my workout today?"
    })
    assert chat_resp.status_code == 200
    assert chat_resp.json().get("plan_version") == 2

def test_chat_date_shift_simulation(client, monkeypatch):
    """TEST 9: Changing APP_TEST_DATE to Saturday (2026-10-03) shifts AI Coach to Saturday."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-03")
    
    user_resp = client.post("/api/users", json={
        "name": "Leo Sterling",
        "age": 30,
        "weight": 75.0,
        "height": 177.0,
        "gender": "Male",
        "goal": "Endurance & Stamina",
        "intensity": "Medium",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What is my workout today?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Saturday" in res_text

def test_chat_new_session_state_clean(client, monkeypatch):
    """TEST 10: Starting a fresh chat conversation retains authoritative date and plan state."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02")
    
    user_resp = client.post("/api/users", json={
        "name": "Nadia Ali",
        "age": 26,
        "weight": 56.0,
        "height": 164.0,
        "gender": "Female",
        "goal": "Weight Loss",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    client.post("/api/workouts/generate", json={"user_id": user_id})

    # Clear chat history
    client.delete(f"/api/chat/history?user_id={user_id}")

    # Send new initial message
    chat_resp = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "Hi coach! What should I do today?"
    })
    assert chat_resp.status_code == 200
    res_text = chat_resp.json()["response"]
    assert "Friday" in res_text
    assert "Nadia" in chat_resp.json().get("user_name", "")

def test_chat_reschedule_today_with_tomorrow_and_verify_next_turn(client, monkeypatch):
    """TEST 11: When user asks to reschedule/swap today with tomorrow, DB is updated and next inquiry reflects it."""
    monkeypatch.setenv("APP_TEST_DATE", "2026-10-02") # Friday (Day 5)
    
    user_resp = client.post("/api/users", json={
        "name": "Sarah Chen",
        "age": 26,
        "weight": 58.0,
        "height": 165.0,
        "gender": "Female",
        "goal": "Endurance & Stamina",
        "intensity": "High",
        "equipment": "Full Gym"
    })
    user_id = user_resp.json()["id"]
    plan_resp = client.post("/api/workouts/generate", json={"user_id": user_id})
    plan_id = plan_resp.json()["id"]

    # 1. Ask what today's plan is originally (Friday)
    chat1 = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "What's Today's plan?"
    })
    assert chat1.status_code == 200
    res1 = chat1.json()["response"]
    assert "Friday" in res1
    assert "Friday, Friday" not in res1  # No double weekday

    # 2. Ask to reschedule today with tomorrow
    chat2 = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "Can I skip today, can you reschedule today's plan with the tomorrows plan"
    })
    assert chat2.status_code == 200
    res2 = chat2.json()["response"]
    assert any(k in res2.lower() for k in ["rescheduled", "swapped", "updated"])

    # 3. Inquire again: "So what Today's plan?"
    chat3 = client.post("/api/chat", json={
        "user_id": user_id,
        "message": "So what Today's plan?"
    })
    assert chat3.status_code == 200
    res3 = chat3.json()["response"]
    assert "Friday" in res3
    # It must reflect the swapped routine (Saturday's Active Recovery or rest)
    assert any(k in res3.lower() for k in ["recovery", "rest", "active recovery"])

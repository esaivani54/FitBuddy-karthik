from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)  # in kg
    gender = Column(String(50), nullable=True, default="Not specified")
    height = Column(Float, nullable=True, default=175.0)  # in cm
    goal = Column(String(100), nullable=False)  # Weight Loss, Muscle Gain, General Wellness, etc.
    intensity = Column(String(50), nullable=False)  # Low, Medium, High
    experience = Column(String(50), nullable=True, default="Intermediate")  # Beginner, Intermediate, Advanced
    equipment = Column(String(100), nullable=True, default="Full Gym")  # Full Gym, Dumbbells, Bodyweight
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan", order_by="desc(WorkoutPlan.version)")
    nutrition_guidance = relationship("NutritionGuidance", back_populates="user", cascade="all, delete-orphan", order_by="desc(NutritionGuidance.created_at)")
    daily_logs = relationship("DailyWorkoutLog", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan", order_by="asc(ChatMessage.created_at)")

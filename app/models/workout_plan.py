from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    plan_title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=True)
    target_goal = Column(String(100), nullable=False)
    intensity = Column(String(50), nullable=False)
    
    # JSON containing structured 7-day plan
    days_data = Column(JSON, nullable=False)
    
    # Feedback string or history that resulted in this version
    feedback = Column(Text, nullable=True)
    feedback_history = Column(JSON, nullable=True, default=list)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="workout_plans")
    daily_logs = relationship("DailyWorkoutLog", back_populates="workout_plan", cascade="all, delete-orphan")

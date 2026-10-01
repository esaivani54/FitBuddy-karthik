from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class DailyWorkoutLog(Base):
    __tablename__ = "daily_workout_logs"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)  # 1 to 7
    completed = Column(Boolean, default=False)
    completed_exercises = Column(JSON, nullable=True, default=list)  # list of exercise names or indices completed
    duration_minutes = Column(Integer, nullable=True, default=0)
    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    workout_plan = relationship("WorkoutPlan", back_populates="daily_logs")
    user = relationship("User", back_populates="daily_logs")

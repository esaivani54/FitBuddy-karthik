from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class NutritionGuidance(Base):
    __tablename__ = "nutrition_guidances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal = Column(String(100), nullable=False)
    calorie_estimate = Column(String(100), nullable=True)
    macro_split = Column(JSON, nullable=True)  # {"protein": "140g (30%)", "carbs": "220g (45%)", "fats": "55g (25%)"}
    daily_tips = Column(JSON, nullable=False)  # {"nutrition": "...", "hydration": "...", "recovery": "...", "sleep": "..."}
    hydration_target = Column(String(100), nullable=True, default="3.0 - 3.5 Liters daily")
    recovery_protocols = Column(JSON, nullable=True)  # list of protocol strings
    sleep_target = Column(String(100), nullable=True, default="7.5 - 8.5 hours")
    disclaimer = Column(Text, nullable=True, default="FitBuddy provides general fitness and wellness information and is not a substitute for professional medical advice or personalized clinical nutrition guidance.")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="nutrition_guidance")

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class AdminStatsResponse(BaseModel):
    total_users: int
    total_plans: int
    total_regenerations: int
    completed_workouts: int
    goal_distribution: Dict[str, int]
    intensity_distribution: Dict[str, int]
    recent_activity: List[Dict[str, Any]]

class AdminUserItem(BaseModel):
    id: int
    name: str
    age: int
    weight: float
    goal: str
    intensity: str
    plan_count: int
    active_version: Optional[int] = 1
    last_active: datetime
    created_at: datetime

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse

logger = logging.getLogger("fitbuddy.api_users")
router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create a new user profile")
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Validates user metrics and creates a new user profile."""
    user = User(
        name=user_in.name,
        age=user_in.age,
        weight=user_in.weight,
        gender=user_in.gender,
        height=user_in.height,
        goal=user_in.goal,
        intensity=user_in.intensity,
        experience=user_in.experience,
        equipment=user_in.equipment
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/{user_id}", response_model=UserResponse, summary="Get user profile by ID")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")
    return user

@router.put("/{user_id}", response_model=UserResponse, summary="Update user profile")
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

@router.get("", response_model=List[UserResponse], summary="List all users")
def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()

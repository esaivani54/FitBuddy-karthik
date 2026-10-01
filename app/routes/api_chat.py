import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryItem
from app.services.chat_service import chat_service

logger = logging.getLogger("fitbuddy.api_chat")
router = APIRouter(prefix="/api/chat", tags=["AI Chatbot"])

@router.post("", response_model=ChatResponse, summary="Chat in real-time with FitBuddy AI Coach")
def chat_with_coach(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Real-time AI Sports Science & Fitness Coach chatbot endpoint.
    Retrieves the athlete's biometrics, active workout plan split, and nutrition targets.
    Persists conversations in SQLite and detects plan modification intents.
    """
    try:
        result = chat_service.process_chat(
            db=db,
            user_id=req.user_id,
            message=req.message
        )
        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}"
        )

@router.get("/history", summary="Get stored conversation history")
def get_chat_history(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Returns persistent message history for user."""
    target_user_id = user_id
    if not target_user_id:
        user = db.query(User).first()
        target_user_id = user.id if user else None

    if not target_user_id:
        return []

    messages = chat_service.get_history(db, target_user_id, limit=40)
    return [{
        "id": m.id,
        "role": m.role,
        "message": m.message,
        "created_at": m.created_at.strftime("%H:%M")
    } for m in messages]

@router.delete("/history", summary="Clear chat history")
def clear_chat_history(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Deletes conversation records for the user."""
    target_user_id = user_id
    if not target_user_id:
        user = db.query(User).first()
        target_user_id = user.id if user else None

    if target_user_id:
        chat_service.clear_history(db, target_user_id)
    return {"status": "success", "message": "Conversation history cleared"}

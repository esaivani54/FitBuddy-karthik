import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.user import User
from app.models.workout_plan import WorkoutPlan
from app.models.daily_log import DailyWorkoutLog
from app.models.nutrition_tip import NutritionGuidance
from app.models.chat_message import ChatMessage
from app.services.ai_service import ai_service
from app.services.workout_service import workout_service
from app.utils.date_context import build_authoritative_chat_context, get_current_app_date, WEEKDAY_NAMES, resolve_day_by_weekday_name

logger = logging.getLogger("fitbuddy.chat_service")

class ChatService:
    def get_history(self, db: Session, user_id: int, limit: int = 30) -> List[ChatMessage]:
        """Retrieves recent conversation turns for the user."""
        return db.query(ChatMessage).filter(
            ChatMessage.user_id == user_id
        ).order_by(ChatMessage.created_at.asc()).limit(limit).all()

    def save_message(self, db: Session, user_id: int, role: str, message: str, conversation_id: str = "default") -> ChatMessage:
        """Persists a single message in the database."""
        msg = ChatMessage(
            user_id=user_id,
            role=role,
            message=message,
            conversation_id=conversation_id,
            created_at=datetime.utcnow()
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def clear_history(self, db: Session, user_id: int):
        """Clears stored messages for the user."""
        db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
        db.commit()

    def process_chat(self, db: Session, user_id: Optional[int], message: str) -> Dict[str, Any]:
        """
        Coordinates authoritative AI Coach flow:
        1. Identifies user & retrieves actual DB profile, active plan, nutrition targets, completed logs.
        2. Resolves current date and today's workout via authoritative date context.
        3. Detects day swap/reschedule requests and persists modifications directly to the database.
        4. Logs AI context for debugging.
        5. Retrieves recent conversation context.
        6. Generates AI response using Gemini / rich context-aware heuristic engine.
        7. Detects plan modification requests and offers explicit one-click confirmation.
        8. Persists conversation in SQLite.
        """
        user: Optional[User] = None
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()

        if not user:
            user = db.query(User).order_by(desc(User.id)).first() or db.query(User).first()

        actual_user_id = user.id if user else None

        user_info = {
            "name": user.name if user else "Friend",
            "age": user.age if user else 28,
            "weight": user.weight if user else 70.0,
            "height": user.height if user else 175.0,
            "gender": user.gender if user else "Not specified",
            "goal": user.goal if user else "General Wellness",
            "intensity": user.intensity if user else "Medium",
            "equipment": user.equipment if user else "Full Gym"
        }

        active_plan_dict = None
        nutrition_dict = None
        completed_days_map = {}
        active_plan = None

        if user:
            # Always get the latest active plan version
            active_plan = db.query(WorkoutPlan).filter(
                WorkoutPlan.user_id == user.id,
                WorkoutPlan.is_active == True
            ).first()

            if not active_plan:
                active_plan = db.query(WorkoutPlan).filter(
                    WorkoutPlan.user_id == user.id
                ).order_by(desc(WorkoutPlan.version)).first()

            if active_plan:
                active_plan_dict = {
                    "id": active_plan.id,
                    "plan_title": active_plan.plan_title,
                    "version": active_plan.version,
                    "summary": active_plan.summary,
                    "target_goal": active_plan.target_goal,
                    "intensity": active_plan.intensity,
                    "days": active_plan.days_data
                }

                # Fetch completed workout logs for this active plan
                logs = db.query(DailyWorkoutLog).filter(
                    DailyWorkoutLog.plan_id == active_plan.id,
                    DailyWorkoutLog.completed == True
                ).all()
                completed_days_map = {l.day_number: l for l in logs}

            nutrition_plan = db.query(NutritionGuidance).filter(
                NutritionGuidance.user_id == user.id
            ).first()

            if nutrition_plan:
                nutrition_dict = {
                    "calorie_estimate": nutrition_plan.calorie_estimate,
                    "macro_split": nutrition_plan.macro_split,
                    "hydration_target": nutrition_plan.hydration_target,
                    "sleep_target": nutrition_plan.sleep_target,
                    "daily_tips": nutrition_plan.daily_tips
                }

        # Build initial authoritative context
        auth_context = build_authoritative_chat_context(
            user_info=user_info,
            active_plan_dict=active_plan_dict,
            nutrition_dict=nutrition_dict,
            completed_days_map=completed_days_map
        )

        msg_lower = message.lower()

        # Check for Reschedule / Day Swap Intent in user's active plan
        is_reschedule_swap = False
        reschedule_result = None

        swap_keywords = ["reschedule", "swap", "postpone", "push today", "skip today", "switch today", "move today", "trade today"]
        if any(k in msg_lower for k in swap_keywords) and active_plan and user:
            # 1. Swapping today with tomorrow / skipping today to tomorrow
            if (("today" in msg_lower or "skip" in msg_lower) and "tomorrow" in msg_lower) or \
               ("reschedule today" in msg_lower) or \
               ("swap today" in msg_lower) or \
               ("postpone today" in msg_lower) or \
               ("push today" in msg_lower) or \
               ("skip today" in msg_lower):

                source_day_num = auth_context.get("today_day_number", 5)
                target_day_num = 1 if source_day_num == 7 else (source_day_num + 1)
                reschedule_result = workout_service.swap_plan_days(
                    db=db,
                    user_id=user.id,
                    source_day_num=source_day_num,
                    target_day_num=target_day_num,
                    plan_id=active_plan.id
                )
                if reschedule_result:
                    is_reschedule_swap = True

            # 2. Swapping specific weekdays (e.g., "swap Friday and Saturday")
            elif any(w.lower() in msg_lower for w in WEEKDAY_NAMES):
                mentioned = [w for w in WEEKDAY_NAMES if w.lower() in msg_lower]
                if len(mentioned) >= 2:
                    d_a_num, _, _ = resolve_day_by_weekday_name(active_plan.days_data or [], mentioned[0])
                    d_b_num, _, _ = resolve_day_by_weekday_name(active_plan.days_data or [], mentioned[1])
                    if d_a_num and d_b_num and d_a_num != d_b_num:
                        reschedule_result = workout_service.swap_plan_days(
                            db=db,
                            user_id=user.id,
                            source_day_num=d_a_num,
                            target_day_num=d_b_num,
                            plan_id=active_plan.id
                        )
                        if reschedule_result:
                            is_reschedule_swap = True

        # If day swap occurred, refresh plan from database and rebuild auth_context
        if is_reschedule_swap and reschedule_result:
            db.refresh(active_plan)
            active_plan_dict = {
                "id": active_plan.id,
                "plan_title": active_plan.plan_title,
                "version": active_plan.version,
                "summary": active_plan.summary,
                "target_goal": active_plan.target_goal,
                "intensity": active_plan.intensity,
                "days": active_plan.days_data
            }
            auth_context = build_authoritative_chat_context(
                user_info=user_info,
                active_plan_dict=active_plan_dict,
                nutrition_dict=nutrition_dict,
                completed_days_map=completed_days_map
            )

        # Log AI Context for developer debugging per requirement Section 19
        today_w = auth_context.get("today_workout") or {}
        logger.info(
            f"\n============================================================\n"
            f"AI CONTEXT\n"
            f"User: {actual_user_id} ({user_info.get('name')})\n"
            f"Date: {auth_context.get('current_date')}\n"
            f"Day: {auth_context.get('current_weekday')}\n"
            f"Plan ID: {active_plan.id if active_plan else 'None'}\n"
            f"Plan Version: {active_plan.version if active_plan else 'None'}\n"
            f"Resolved Day: {auth_context.get('today_weekday')} (Day {auth_context.get('today_day_number')})\n"
            f"Workout: {today_w.get('workout_title', 'None')}\n"
            f"============================================================"
        )

        # 1. Fetch recent database history
        past_msgs = []
        if actual_user_id:
            db_history = self.get_history(db, actual_user_id, limit=8)
            past_msgs = [{"role": m.role, "content": m.message} for m in db_history]

        # 2. Persist incoming user message
        if actual_user_id:
            self.save_message(db, actual_user_id, "user", message)

        # 3. Check for Plan Modification Request Intent
        is_plan_change = any(phrase in msg_lower for phrase in [
            "change my weekly plan", "update my plan", "more cardio in my plan",
            "fewer days", "more days", "shorten my workouts", "regenerate my plan",
            "modify my routine", "remove leg day from my plan"
        ])

        # 4. Generate AI response
        if is_reschedule_swap and reschedule_result:
            src_name = reschedule_result["source_day_name"]
            src_title = reschedule_result["source_new_title"]
            src_focus = reschedule_result["source_new_focus"]
            src_rest = reschedule_result["source_new_is_rest"]

            tgt_name = reschedule_result["target_day_name"]
            tgt_title = reschedule_result["target_new_title"]
            tgt_focus = reschedule_result["target_new_focus"]
            tgt_rest = reschedule_result["target_new_is_rest"]

            src_status = f"**{src_title}**" + (f" (Focus: {src_focus})" if src_focus else "") if not src_rest else "**Active Recovery & Rest**"
            tgt_status = f"**{tgt_title}**" + (f" (Focus: {tgt_focus})" if tgt_focus else "") if not tgt_rest else "**Active Recovery & Rest**"

            first_name = user.name.split()[0] if user and user.name else "Friend"

            ai_reply = (
                f"✅ **Plan Rescheduled in Database!**\n\n"
                f"I've updated your active training schedule directly in your blueprint, {first_name}:\n\n"
                f"• **Today ({src_name}):** Swapped to {src_status}\n"
                f"• **Tomorrow ({tgt_name}):** Swapped to {tgt_status}\n\n"
                f"Your live Dashboard and Daily Workout trackers have been immediately updated with this new schedule. "
                f"Feel free to take today to recover, and you'll crush your workout tomorrow! 💪"
            )
        else:
            ai_reply = ai_service.generate_chat_response(
                user_info=user_info,
                current_plan=active_plan_dict,
                nutrition=nutrition_dict,
                message=message,
                chat_history=past_msgs,
                context=auth_context
            )

        suggested_action = None
        if is_plan_change and active_plan_dict and user:
            suggested_action = {
                "type": "regenerate_plan",
                "label": "⚡ Update & Regenerate Plan Now",
                "feedback": message,
                "url": f"/refine?user_id={user.id}&plan_id={active_plan_dict['id']}"
            }

        # 5. Persist assistant response
        if actual_user_id:
            self.save_message(db, actual_user_id, "assistant", ai_reply)

        return {
            "response": ai_reply,
            "user_id": actual_user_id,
            "user_name": user.name if user else "Friend",
            "plan_version": active_plan_dict.get("version") if active_plan_dict else None,
            "suggested_action": suggested_action,
            "timestamp": datetime.now().strftime("%H:%M")
        }

chat_service = ChatService()

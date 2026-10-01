import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.config import settings
from app.schemas.workout import WorkoutPlanDataSchema, DayWorkoutSchema, ExerciseSchema, WarmupItemSchema, CooldownItemSchema
from app.schemas.nutrition import NutritionDataSchema, MacroSplitSchema, DailyTipsSchema
from app.utils.date_context import (
    get_current_app_date,
    format_date_long,
    resolve_plan_day,
    resolve_query_target_day,
    build_authoritative_chat_context,
    resolve_day_by_weekday_name,
    WEEKDAY_NAMES
)

logger = logging.getLogger("fitbuddy.ai_service")

class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.workout_model = settings.GEMINI_WORKOUT_MODEL
        self.nutrition_model = settings.GEMINI_NUTRITION_MODEL
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
                logger.info("Google GenAI client successfully initialized.")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}. Falling back to REST/Heuristic mode.")

    def _call_gemini_api(self, prompt: str, model: str) -> Optional[str]:
        """Calls Gemini API via google-genai client or HTTP REST fallback with candidate model recovery."""
        if not self.api_key:
            return None
        
        candidate_models = [model]
        for fallback in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-pro", "gemini-1.5-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        # 1. Try google-genai client
        if self._client:
            for m in candidate_models:
                try:
                    response = self._client.models.generate_content(
                        model=m,
                        contents=prompt,
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    logger.debug(f"Gemini Client API attempt with {m} failed: {e}")

        # 2. Fallback to direct HTTP request using httpx
        try:
            import httpx
            for m in candidate_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 4096
                    }
                }
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                return parts[0]["text"]
                    else:
                        logger.debug(f"Gemini REST endpoint {m} status {resp.status_code}")
        except Exception as e:
            logger.debug(f"Gemini REST call exception: {e}")

        logger.info("Using FitBuddy high-fidelity sports science heuristic engine.")
        return None

    def _extract_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Extracts and parses JSON from markdown code fences or plain text."""
        if not raw_text:
            return None
        
        # Look for markdown JSON block
        json_pattern = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        candidate = json_pattern.group(1) if json_pattern else raw_text.strip()
        
        # Find first { or [ to last } or ]
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1:
            candidate = candidate[start:end+1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e} for candidate: {candidate[:200]}")
            return None

    def generate_workout_plan(self, user_info: Dict[str, Any]) -> WorkoutPlanDataSchema:
        """
        Generates a 7-day personalized workout plan using Gemini 1.5 Pro or intelligent heuristic.
        """
        prompt = f"""
You are FitBuddy's Elite Sports Scientist and Master Strength & Conditioning Coach.
Create a comprehensive, personalized 7-day workout plan for the following user:

USER PROFILE:
- Name: {user_info.get('name')}
- Age: {user_info.get('age')} years old
- Weight: {user_info.get('weight')} kg
- Height: {user_info.get('height', 175)} cm
- Gender: {user_info.get('gender', 'Not specified')}
- Primary Goal: {user_info.get('goal')}
- Intensity Preference: {user_info.get('intensity')}
- Experience Level: {user_info.get('experience', 'Intermediate')}
- Available Equipment: {user_info.get('equipment', 'Full Gym')}

STRICT REQUIREMENTS:
1. Return exactly 7 days (Day 1 through Day 7).
2. For high intensity: 4-5 training days, 2-3 active recovery/rest days.
3. For medium intensity: 3-4 training days, 3-4 recovery days.
4. For low intensity: 3 light training days, 4 recovery/mobility days.
5. Provide specific warmup (2-3 items), main exercises (3-6 exercises with sets, reps, rest, target muscles, tempo, and form cues), cooldown (2-3 items), and a daily recovery note.
6. For designated rest days, mark 'is_rest_day': true and provide gentle mobility/recovery steps.
7. Return ONLY valid JSON matching this exact JSON structure (no markdown wrappers, no commentary):

{{
  "plan_title": "7-Day Hypertrophy & Fat Loss Blueprint",
  "summary": "Targeted periodized routine designed to optimize muscle retention while accelerating metabolic burn.",
  "target_goal": "{user_info.get('goal')}",
  "intensity": "{user_info.get('intensity')}",
  "days": [
    {{
      "day_number": 1,
      "day_name": "Monday",
      "workout_title": "Upper Body Power & Hypertrophy",
      "focus": "Chest, Shoulders & Triceps",
      "duration_minutes": 45,
      "is_rest_day": false,
      "warmup": [
        {{"exercise": "Arm Circles & Band Pull-Aparts", "duration_or_reps": "3 mins"}},
        {{"exercise": "Scapular Push-ups", "duration_or_reps": "2 sets of 12 reps"}}
      ],
      "exercises": [
        {{
          "name": "Barbell Bench Press",
          "sets": 4,
          "reps": "8-10 reps",
          "rest": "90 sec",
          "target_muscles": "Pectorals, Anterior Deltoid",
          "tempo": "3-0-1",
          "notes": "Keep shoulder blades retracted and drive through feet."
        }}
      ],
      "cooldown": [
        {{"exercise": "Doorway Chest Stretch", "duration_or_reps": "45s per side"}},
        {{"exercise": "Overhead Triceps Stretch", "duration_or_reps": "30s hold"}}
      ],
      "recovery_note": "Rehydrate with electrolyte water and consume 30g protein within 60 minutes."
    }}
    // Repeat for all 7 days exactly
  ]
}}
"""
        raw_response = self._call_gemini_api(prompt, self.workout_model)
        if raw_response:
            parsed = self._extract_json(raw_response)
            if parsed:
                try:
                    return WorkoutPlanDataSchema(**parsed)
                except Exception as val_err:
                    logger.warning(f"AI response schema validation error: {val_err}. Using fallback generator.")
        
        # Fallback to local heuristic generator
        return self._generate_heuristic_workout(user_info)

    def regenerate_workout_plan(self, user_info: Dict[str, Any], current_plan: Dict[str, Any], feedback: str, quick_tags: List[str]) -> WorkoutPlanDataSchema:
        """
        Regenerates and adapts the workout plan based on user feedback and existing plan constraints.
        """
        prompt = f"""
You are FitBuddy's Elite AI Fitness Coach.
A user wants to refine their existing 7-day workout plan.

USER PROFILE:
- Name: {user_info.get('name')}
- Age: {user_info.get('age')} years
- Weight: {user_info.get('weight')} kg
- Primary Goal: {user_info.get('goal')}
- Intensity: {user_info.get('intensity')}

CURRENT PLAN SUMMARY:
- Title: {current_plan.get('plan_title')}
- Summary: {current_plan.get('summary')}

USER FEEDBACK & REQUESTED MODIFICATIONS:
- Direct Request: "{feedback}"
- Quick Tags Selected: {', '.join(quick_tags) if quick_tags else 'None'}

INSTRUCTIONS:
1. Preserve the user's core safety and physiological goals.
2. Directly adapt the routine to incorporate the user's specific feedback (e.g. if they asked for more cardio, add HIIT/zone 2 cardio sessions; if they requested more rest, convert a training day into an active recovery day; if they want shorter sessions, adjust sets and duration).
3. Return the complete updated 7-day schedule with all exercises, warmups, cooldowns, and recovery notes.
4. Output ONLY valid JSON matching the exact WorkoutPlanDataSchema.
"""
        raw_response = self._call_gemini_api(prompt, self.workout_model)
        if raw_response:
            parsed = self._extract_json(raw_response)
            if parsed:
                try:
                    return WorkoutPlanDataSchema(**parsed)
                except Exception as val_err:
                    logger.warning(f"Regenerated AI response validation error: {val_err}. Using heuristic updater.")

        # Fallback heuristic regeneration
        return self._regenerate_heuristic_workout(user_info, current_plan, feedback, quick_tags)

    def generate_nutrition_tip(self, user_info: Dict[str, Any]) -> NutritionDataSchema:
        """
        Generates goal-specific nutrition, hydration, and recovery guidance using Gemini Flash.
        """
        prompt = f"""
You are FitBuddy's Sports Nutritionist and Recovery Specialist.
Generate structured, goal-calibrated nutrition and recovery guidance for:

USER:
- Name: {user_info.get('name')}
- Age: {user_info.get('age')}
- Weight: {user_info.get('weight')} kg
- Goal: {user_info.get('goal')}
- Intensity: {user_info.get('intensity')}

Output ONLY valid JSON with this exact structure:
{{
  "goal": "{user_info.get('goal')}",
  "macro_split": {{
    "protein": "150g (30%) - 2.0g per kg bodyweight for tissue repair",
    "carbohydrates": "200g (40%) - Complex carbs for glycogen replenishment",
    "fats": "65g (30%) - Healthy unsaturated fats for hormone balance",
    "calories_estimate": "2,200 - 2,400 kcal daily target"
  }},
  "daily_tips": {{
    "nutrition": "Prioritize whole food protein sources within 2 hours post-workout. Distribute protein intake across 4 balanced meals.",
    "hydration": "Consume 500ml water upon waking, and 250ml every 20 minutes during exercise sessions.",
    "recovery": "Engage in 10 minutes of light foam rolling for quads and thoracic spine on high-volume days.",
    "sleep": "Target 8 hours of uninterrupted sleep in a 18-20°C dark room to optimize growth hormone release."
  }},
  "hydration_target": "3.2 - 3.8 Liters daily",
  "recovery_protocols": [
    "Post-workout 5-minute contrast shower or diaphragmatic breathing",
    "Daily 10,000 steps baseline non-exercise physical activity",
    "Epsom salt bath or 15-min lower limb elevation on heavy leg days"
  ],
  "sleep_target": "7.5 - 8.5 hours",
  "disclaimer": "FitBuddy provides fitness & wellness recommendations for informational purposes only. Consult a registered healthcare professional before making substantial dietary changes."
}}
"""
        raw_response = self._call_gemini_api(prompt, self.nutrition_model)
        if raw_response:
            parsed = self._extract_json(raw_response)
            if parsed:
                try:
                    return NutritionDataSchema(**parsed)
                except Exception as val_err:
                    logger.warning(f"Nutrition AI schema validation error: {val_err}. Using heuristic nutrition.")

        return self._generate_heuristic_nutrition(user_info)

    # -------------------------------------------------------------------------
    # High-Fidelity Heuristic Fallback Engines
    # -------------------------------------------------------------------------
    def _generate_heuristic_workout(self, user_info: Dict[str, Any]) -> WorkoutPlanDataSchema:
        goal = user_info.get("goal", "General Wellness")
        intensity = user_info.get("intensity", "Medium")
        name = user_info.get("name", "Athlete")
        weight = float(user_info.get("weight", 70.0))

        if "Loss" in goal or "Fat" in goal:
            return self._build_weight_loss_plan(name, goal, intensity, weight)
        elif "Muscle" in goal or "Hypertrophy" in goal or "Strength" in goal:
            return self._build_muscle_gain_plan(name, goal, intensity, weight)
        elif "Endurance" in goal or "Stamina" in goal:
            return self._build_endurance_plan(name, goal, intensity, weight)
        else:
            return self._build_wellness_plan(name, goal, intensity, weight)

    def _build_muscle_gain_plan(self, name: str, goal: str, intensity: str, weight: float) -> WorkoutPlanDataSchema:
        dur = 55 if intensity == "High" else (45 if intensity == "Medium" else 35)
        days = [
            DayWorkoutSchema(
                day_number=1,
                day_name="Monday",
                workout_title="Upper Body Strength & Chest Focus",
                focus="Pectorals, Anterior Deltoids, Triceps",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Arm Circles & Dynamic Shoulder Rotations", duration_or_reps="3 mins"),
                    WarmupItemSchema(exercise="Push-Up Plus & Scapular Wall Slides", duration_or_reps="2 sets × 10 reps")
                ],
                exercises=[
                    ExerciseSchema(name="Barbell Flat Bench Press", sets=4, reps="8-10 reps", rest="90 sec", target_muscles="Chest, Triceps", tempo="3-0-1", notes="Control the eccentric phase, pause slightly at chest."),
                    ExerciseSchema(name="Incline Dumbbell Press", sets=3, reps="10-12 reps", rest="75 sec", target_muscles="Upper Chest, Front Delts", tempo="2-0-2", notes="30-degree incline, squeeze at the top."),
                    ExerciseSchema(name="Seated Cable Rows", sets=3, reps="10-12 reps", rest="60 sec", target_muscles="Lats, Rhomboids", tempo="2-1-2", notes="Drive elbows back, avoid excessive torso swing."),
                    ExerciseSchema(name="Standing Dumbbell Lateral Raises", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Lateral Deltoid", tempo="2-0-2", notes="Lead with elbows, slight forward lean."),
                    ExerciseSchema(name="Rope Cable Triceps Pushdowns", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Triceps", tempo="2-0-1", notes="Spread rope at bottom for full lockout.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Doorway Pectoral Stretch", duration_or_reps="45s hold per side"),
                    CooldownItemSchema(exercise="Cross-Body Shoulder Stretch", duration_or_reps="30s hold per side")
                ],
                recovery_note="Replenish with 30-40g high-bioavailability protein and 500ml water within 45 minutes."
            ),
            DayWorkoutSchema(
                day_number=2,
                day_name="Tuesday",
                workout_title="Lower Body Hypertrophy & Quad Dominance",
                focus="Quadriceps, Hamstrings, Calves",
                duration_minutes=dur + 5,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Bodyweight Air Squats & Hip Openers", duration_or_reps="4 mins"),
                    WarmupItemSchema(exercise="Glute Bridges & Leg Swings", duration_or_reps="2 sets × 12 reps")
                ],
                exercises=[
                    ExerciseSchema(name="Barbell Back Squat or Hack Squat", sets=4, reps="6-8 reps", rest="120 sec", target_muscles="Quads, Glutes", tempo="3-1-1", notes="Keep chest proud, drive through midfoot."),
                    ExerciseSchema(name="Romanian Deadlifts (Dumbbell/Barbell)", sets=3, reps="8-10 reps", rest="90 sec", target_muscles="Hamstrings, Glutes", tempo="3-1-1", notes="Hinge hips back, feel hamstring stretch."),
                    ExerciseSchema(name="Bulgarian Split Squats", sets=3, reps="10 reps/leg", rest="60 sec", target_muscles="Quads, Glute Medius", tempo="2-0-1", notes="Stay upright for quads, slight forward lean for glutes."),
                    ExerciseSchema(name="Seated or Lying Leg Curls", sets=3, reps="12-15 reps", rest="60 sec", target_muscles="Hamstrings", tempo="2-1-2", notes="Slow and controlled on negative."),
                    ExerciseSchema(name="Standing Calf Raises", sets=4, reps="15 reps", rest="45 sec", target_muscles="Gastrocnemius", tempo="2-2-1", notes="Hold peak contraction for 2 full seconds.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Standing Quad & Hip Flexor Stretch", duration_or_reps="45s per side"),
                    CooldownItemSchema(exercise="Seated Hamstring Forward Fold", duration_or_reps="60s hold")
                ],
                recovery_note="Elevate legs for 10 minutes post-session to facilitate venous return and reduce soreness."
            ),
            DayWorkoutSchema(
                day_number=3,
                day_name="Wednesday",
                workout_title="Active Rest, Mobility & Core Stabilization",
                focus="Thoracic Mobility, Hip Flexors, Deep Core",
                duration_minutes=30,
                is_rest_day=True,
                warmup=[
                    WarmupItemSchema(exercise="Cat-Cow & Bird-Dog Flow", duration_or_reps="5 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Zone 2 Brisk Walking / Incline Treadmill", sets=1, reps="20 mins", rest="None", target_muscles="Cardiovascular, Aerobic Base", tempo="Continuous", notes="Maintain nasal breathing conversational pace."),
                    ExerciseSchema(name="Deadbugs with Core Compression", sets=3, reps="12 reps/side", rest="45 sec", target_muscles="Transverse Abdominis", tempo="3-1-2", notes="Keep lower back flat against the floor."),
                    ExerciseSchema(name="Side Planks with Hip Abduction", sets=3, reps="30s/side", rest="45 sec", target_muscles="Obliques, QL", tempo="Static", notes="Maintain straight alignment from head to heels.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Child's Pose with Lateral Reach", duration_or_reps="60s hold"),
                    CooldownItemSchema(exercise="World's Greatest Stretch Flow", duration_or_reps="5 reps/side")
                ],
                recovery_note="Prioritize hydration with electrolytes and get at least 8 hours of restorative sleep."
            ),
            DayWorkoutSchema(
                day_number=4,
                day_name="Thursday",
                workout_title="Posterior Chain, Back & Biceps Focus",
                focus="Lats, Upper Back, Rear Delts, Biceps",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Band Pull-Aparts & Y-T-W Raises", duration_or_reps="3 mins"),
                    WarmupItemSchema(exercise="Hanging Scapular Retractions", duration_or_reps="2 sets × 8 reps")
                ],
                exercises=[
                    ExerciseSchema(name="Lat Pulldowns or Pull-Ups", sets=4, reps="8-10 reps", rest="90 sec", target_muscles="Latissimus Dorsi", tempo="3-0-1", notes="Pull elbows down into pockets, initiate from lats."),
                    ExerciseSchema(name="Chest-Supported T-Bar or DB Row", sets=3, reps="10-12 reps", rest="75 sec", target_muscles="Rhomboids, Mid Traps", tempo="2-1-1", notes="Eliminate lower back strain by supporting torso."),
                    ExerciseSchema(name="Face Pulls with External Rotation", sets=3, reps="15 reps", rest="45 sec", target_muscles="Rear Deltoids, Rotator Cuff", tempo="2-1-2", notes="Pull to eye level, thumbs facing backward."),
                    ExerciseSchema(name="Incline Dumbbell Biceps Curls", sets=3, reps="10-12 reps", rest="60 sec", target_muscles="Biceps Long Head", tempo="3-0-1", notes="Full stretch at bottom, do not swing."),
                    ExerciseSchema(name="Hammer Curls", sets=3, reps="12 reps", rest="45 sec", target_muscles="Brachialis, Forearms", tempo="2-0-1", notes="Neutral grip throughout.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Lat Stretch on Upright Post", duration_or_reps="45s/side"),
                    CooldownItemSchema(exercise="Biceps Wall Stretch", duration_or_reps="30s/side")
                ],
                recovery_note="Consume complex carbohydrates to replenish glycogen stores for muscle synthesis."
            ),
            DayWorkoutSchema(
                day_number=5,
                day_name="Friday",
                workout_title="Shoulders, Arms & Weak Point Refinement",
                focus="Deltoids, Triceps, Biceps, Core",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Rotator Cuff Warmup with Light Band", duration_or_reps="3 mins"),
                    WarmupItemSchema(exercise="Jump Rope or Shadow Boxing", duration_or_reps="3 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Overhead Dumbbell Shoulder Press", sets=4, reps="8-10 reps", rest="90 sec", target_muscles="Anterior & Lateral Delts", tempo="3-0-1", notes="Brace core, press in slight arc overhead."),
                    ExerciseSchema(name="Cable Lateral Raises", sets=3, reps="12-15 reps/side", rest="45 sec", target_muscles="Lateral Deltoid", tempo="2-1-2", notes="Constant tension on cable across full range."),
                    ExerciseSchema(name="Overhead Cable Triceps Extensions", sets=3, reps="12 reps", rest="60 sec", target_muscles="Triceps Long Head", tempo="3-0-1", notes="Keep upper arms stationary."),
                    ExerciseSchema(name="Preacher Curls or EZ-Bar Curls", sets=3, reps="10-12 reps", rest="60 sec", target_muscles="Biceps", tempo="2-1-1", notes="Strict form with no body momentum."),
                    ExerciseSchema(name="Hanging Leg / Knee Raises", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Rectus Abdominis", tempo="2-1-2", notes="Curl pelvis upward to engage abs.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Overhead Triceps & Lat Stretch", duration_or_reps="45s/side"),
                    CooldownItemSchema(exercise="Child's Pose with Deep Breathing", duration_or_reps="60s hold")
                ],
                recovery_note="High protein post-workout meal with micronutrient-rich green vegetables."
            ),
            DayWorkoutSchema(
                day_number=6,
                day_name="Saturday",
                workout_title="Full Body Functional Power & Conditioning",
                focus="Compound Movements, Metabolic Conditioning",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Full Body Dynamic Joint Circles", duration_or_reps="4 mins"),
                    WarmupItemSchema(exercise="Inchworms with Push-up", duration_or_reps="6 reps")
                ],
                exercises=[
                    ExerciseSchema(name="Trap Bar Deadlift or Goblet Squats", sets=4, reps="6-8 reps", rest="90 sec", target_muscles="Glutes, Hamstrings, Quads, Traps", tempo="2-1-1", notes="Neutral spine, explosive drive off floor."),
                    ExerciseSchema(name="Dumbbell Walking Lunges", sets=3, reps="12 paces/leg", rest="60 sec", target_muscles="Quads, Glutes", tempo="2-0-1", notes="Controlled knee drop to 1 inch above floor."),
                    ExerciseSchema(name="Push-Ups to Renegade Rows", sets=3, reps="8-10 reps/side", rest="60 sec", target_muscles="Chest, Upper Back, Core", tempo="2-0-1", notes="Prevent hip rotation during rows."),
                    ExerciseSchema(name="Kettlebell Swings", sets=3, reps="15 reps", rest="60 sec", target_muscles="Posterior Chain, Glutes", tempo="Explosive", notes="Hinge powerfully, snap hips forward."),
                    ExerciseSchema(name="Plank to Downward Dog Flow", sets=3, reps="10 reps", rest="45 sec", target_muscles="Core, Calves, Shoulders", tempo="Smooth", notes="Focus on rhythmic breathing.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Pigeon Pose Hip Stretch", duration_or_reps="60s/side"),
                    CooldownItemSchema(exercise="Cobra Pose Abdominal Stretch", duration_or_reps="45s hold")
                ],
                recovery_note="Take a relaxing 20-minute evening walk and prepare for full Sunday restoration."
            ),
            DayWorkoutSchema(
                day_number=7,
                day_name="Sunday",
                workout_title="Full System Restoration & Weekly Reset",
                focus="Total Body Parasympathetic Recovery",
                duration_minutes=25,
                is_rest_day=True,
                warmup=[
                    WarmupItemSchema(exercise="Gentle Neck and Wrist Mobility", duration_or_reps="3 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Full Body Foam Rolling Protocol", sets=1, reps="15 mins", rest="None", target_muscles="Quads, IT Bands, Lats, Calves", tempo="Slow", notes="Spend 60 seconds on tight tender areas."),
                    ExerciseSchema(name="Deep Box Breathing (4-4-4-4)", sets=1, reps="10 mins", rest="None", target_muscles="Nervous System Reset", tempo="4s in, 4s hold, 4s out, 4s hold", notes="Calms cortisol and primes muscle recovery.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Supine Spinal Twist", duration_or_reps="60s/side"),
                    CooldownItemSchema(exercise="Legs Up the Wall Pose (Viparita Karani)", duration_or_reps="5 mins")
                ],
                recovery_note="Prep meals and plan hydration targets for the upcoming training week."
            )
        ]

        return WorkoutPlanDataSchema(
            plan_title=f"{name}'s 7-Day Hypertrophy & Power Blueprint",
            summary=f"Scientifically structured weekly split calibrated for {intensity} intensity muscle protein synthesis, balanced compound loading, and optimal systemic recovery.",
            target_goal=goal,
            intensity=intensity,
            days=days
        )

    def _build_weight_loss_plan(self, name: str, goal: str, intensity: str, weight: float) -> WorkoutPlanDataSchema:
        dur = 45 if intensity == "High" else (40 if intensity == "Medium" else 30)
        days = [
            DayWorkoutSchema(
                day_number=1,
                day_name="Monday",
                workout_title="Metabolic Upper Body Circuit & Core",
                focus="Chest, Back, Arms & Calorie Burn",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Jumping Jacks & High Knees", duration_or_reps="3 mins"),
                    WarmupItemSchema(exercise="Dynamic Arm & Torso Rotations", duration_or_reps="2 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Dumbbell Thrusters (Squat to Press)", sets=4, reps="12-15 reps", rest="45 sec", target_muscles="Full Body, Shoulders, Quads", tempo="2-0-1", notes="Continuous fluid movement from squat to overhead press."),
                    ExerciseSchema(name="Dumbbell Bent-Over Rows", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Upper Back, Lats", tempo="2-0-1", notes="Keep back flat, squeeze shoulder blades."),
                    ExerciseSchema(name="Push-Ups (or Incline Push-Ups)", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Chest, Triceps, Core", tempo="2-0-1", notes="Maintain straight plank posture."),
                    ExerciseSchema(name="Mountain Climbers", sets=3, reps="40 sec", rest="30 sec", target_muscles="Core, Cardiovascular", tempo="Rapid", notes="Drive knees toward chest without bouncing hips."),
                    ExerciseSchema(name="Bicycle Crunches", sets=3, reps="20 total reps", rest="30 sec", target_muscles="Obliques, Rectus Abdominis", tempo="2-1-2", notes="Slow, deliberate elbow-to-opposite-knee contact.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Chest Doorway Stretch", duration_or_reps="45s/side"),
                    CooldownItemSchema(exercise="Child's Pose", duration_or_reps="60s hold")
                ],
                recovery_note="Stay in a mild caloric deficit with 1.8g protein/kg to preserve lean muscle tissue."
            ),
            DayWorkoutSchema(
                day_number=2,
                day_name="Tuesday",
                workout_title="Lower Body Calorie Furnace & Glutes",
                focus="Quads, Hamstrings, Glutes & EPOC",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Bodyweight Squats & Leg Swings", duration_or_reps="4 mins"),
                    WarmupItemSchema(exercise="High Knee Skips", duration_or_reps="2 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Goblet Squats with Dumbbell/Kettlebell", sets=4, reps="12-15 reps", rest="60 sec", target_muscles="Quads, Glutes", tempo="2-1-1", notes="Keep weight close to chest, descend below parallel."),
                    ExerciseSchema(name="Reverse Lunges with Dumbbells", sets=3, reps="10 reps/leg", rest="45 sec", target_muscles="Glutes, Hamstrings", tempo="2-0-1", notes="Step back gently, 90-degree bend in front knee."),
                    ExerciseSchema(name="Dumbbell Romanian Deadlifts", sets=3, reps="12 reps", rest="45 sec", target_muscles="Hamstrings, Lower Back", tempo="3-1-1", notes="Hinge at hips, maintain slight knee bend."),
                    ExerciseSchema(name="Glute Bridge Pulses", sets=3, reps="20 reps", rest="30 sec", target_muscles="Glutes", tempo="1-1-1", notes="Squeeze at top for 1 full second."),
                    ExerciseSchema(name="Jump Squats / Speed Air Squats", sets=3, reps="30 sec", rest="45 sec", target_muscles="Fast-Twitch Leg Fibers", tempo="Explosive", notes="Land softly on midfoot and absorb impact.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Standing Quad Stretch", duration_or_reps="45s/side"),
                    CooldownItemSchema(exercise="Seated Butterfly Stretch", duration_or_reps="60s hold")
                ],
                recovery_note="Drink minimum 3 liters of water today to flush metabolic waste products."
            ),
            DayWorkoutSchema(
                day_number=3,
                day_name="Wednesday",
                workout_title="Zone 2 Steady-State Cardio & Mobility",
                focus="Fat Oxidation & Aerobic Capacity",
                duration_minutes=35,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Light 3-min Walk & Joint Mobilization", duration_or_reps="3 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Zone 2 Low-Impact Cardio (Incline Walk, Bike, or Elliptical)", sets=1, reps="25 mins", rest="None", target_muscles="Aerobic System, Cardiac Output", tempo="Steady 60-70% Max HR", notes="Ideal fat oxidation zone; should be able to speak full sentences."),
                    ExerciseSchema(name="Standing Calf & Hip Flexor Mobilization", sets=2, reps="45s/side", rest="30 sec", target_muscles="Calves, Psoas", tempo="Smooth", notes="Lengthen hip flexors tight from sitting.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Hamstring Stretch", duration_or_reps="45s/side"),
                    CooldownItemSchema(exercise="Down-Dog Calf Pedaling", duration_or_reps="60s")
                ],
                recovery_note="Optimize lunch with fiber-rich greens and lean white meat or tofu."
            ),
            DayWorkoutSchema(
                day_number=4,
                day_name="Thursday",
                workout_title="High-Intensity Interval Training (HIIT) & Core",
                focus="Cardio Intervals & Abdominal Density",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Butt Kicks & Arm Sweeps", duration_or_reps="3 mins"),
                    WarmupItemSchema(exercise="Plank Walkouts", duration_or_reps="5 reps")
                ],
                exercises=[
                    ExerciseSchema(name="Kettlebell or Dumbbell Swings", sets=4, reps="15 reps", rest="30 sec", target_muscles="Hips, Glutes, Heart Rate", tempo="Explosive", notes="Hinge sharply, power generated by hips."),
                    ExerciseSchema(name="Burpees (or Step-Back Burpees)", sets=3, reps="10-12 reps", rest="45 sec", target_muscles="Full Body Conditioning", tempo="Rhythmic", notes="Maintain steady cadence, avoid collapsing core."),
                    ExerciseSchema(name="Russian Twists (Bodyweight or Light DB)", sets=3, reps="20 total reps", rest="30 sec", target_muscles="Obliques", tempo="2-0-2", notes="Elevate heels for added core tension."),
                    ExerciseSchema(name="Plank Hold with Shoulder Taps", sets=3, reps="30 sec", rest="30 sec", target_muscles="Anti-Rotational Core", tempo="Controlled", notes="Minimize torso swaying."),
                    ExerciseSchema(name="Shadow Boxing / Speed Punches", sets=3, reps="45 sec", rest="30 sec", target_muscles="Shoulders, Cardio", tempo="Rapid", notes="Fast hands, light on toes.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Cobra Pose Abdominal Stretch", duration_or_reps="45s hold"),
                    CooldownItemSchema(exercise="Seated Forward Fold", duration_or_reps="60s hold")
                ],
                recovery_note="Have an electrolyte drink post-workout to replace sodium and potassium lost in sweat."
            ),
            DayWorkoutSchema(
                day_number=5,
                day_name="Friday",
                workout_title="Full Body Functional Tone & Sculpt",
                focus="Compound Resistance & Muscular Endurance",
                duration_minutes=dur,
                is_rest_day=False,
                warmup=[
                    WarmupItemSchema(exercise="Dynamic Side-to-Side Lunges", duration_or_reps="3 mins"),
                    WarmupItemSchema(exercise="Arm Circles & Scapula Pushups", duration_or_reps="2 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Dumbbell Step-Ups onto Bench/Box", sets=3, reps="12 reps/leg", rest="45 sec", target_muscles="Quads, Glutes", tempo="2-0-1", notes="Drive through front heel, do not push off rear toe."),
                    ExerciseSchema(name="Dumbbell Floor Press", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Chest, Triceps", tempo="2-0-1", notes="Elbows touch floor gently, press up."),
                    ExerciseSchema(name="Lat Pulldowns or Resistance Band Pulls", sets=3, reps="12-15 reps", rest="45 sec", target_muscles="Lats, Mid Back", tempo="2-1-2", notes="Chest high, elbows into ribs."),
                    ExerciseSchema(name="Standing Dumbbell Hammer Curls to Press", sets=3, reps="10 reps", rest="45 sec", target_muscles="Biceps, Shoulders", tempo="2-0-1", notes="Fluid combination exercise."),
                    ExerciseSchema(name="Hollow Body Hold", sets=3, reps="25-30 sec", rest="30 sec", target_muscles="Deep Core", tempo="Static", notes="Lower back pressed hard against mat.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Full Body Reach and Lengthen", duration_or_reps="45s"),
                    CooldownItemSchema(exercise="Pigeon Pose", duration_or_reps="45s/side")
                ],
                recovery_note="Refuel with a high-protein dinner like grilled salmon or tofu with quinoa and asparagus."
            ),
            DayWorkoutSchema(
                day_number=6,
                day_name="Saturday",
                workout_title="Outdoor Active Recovery & Nature Walk",
                focus="Non-Exercise Physical Activity (NEPA) & Recovery",
                duration_minutes=40,
                is_rest_day=True,
                warmup=[
                    WarmupItemSchema(exercise="Gentle Joint Rotations", duration_or_reps="3 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Continuous Nature Walk / Casual Cycling", sets=1, reps="30-40 mins", rest="None", target_muscles="Active Recovery, Mind-Body Reset", tempo="Casual", notes="Target 8,000-10,000 steps without inducing muscle soreness."),
                    ExerciseSchema(name="Standing Quad & Calf Stretches", sets=1, reps="10 mins", rest="None", target_muscles="Lower Body Mobility", tempo="Static", notes="Focus on slow, deep belly breathing.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Seated Forward Bend", duration_or_reps="60s hold"),
                    CooldownItemSchema(exercise="Child's Pose", duration_or_reps="60s hold")
                ],
                recovery_note="Enjoy restorative time with family or friends to reduce stress-induced cortisol."
            ),
            DayWorkoutSchema(
                day_number=7,
                day_name="Sunday",
                workout_title="Restoration, Deep Mobility & Prep",
                focus="Fascial Release & Next Week Planning",
                duration_minutes=25,
                is_rest_day=True,
                warmup=[
                    WarmupItemSchema(exercise="Cat-Cow Breathing", duration_or_reps="3 mins")
                ],
                exercises=[
                    ExerciseSchema(name="Foam Rolling (Calves, Hamstrings, Glutes, Back)", sets=1, reps="15 mins", rest="None", target_muscles="Myofascial Tissue", tempo="Slow", notes="Breathe through trigger points."),
                    ExerciseSchema(name="Diaphragmatic Parasympathetic Breathing", sets=1, reps="10 mins", rest="None", target_muscles="Autonomic Nervous System", tempo="5s In, 5s Out", notes="Promotes deep recovery and tissue repair.")
                ],
                cooldown=[
                    CooldownItemSchema(exercise="Corpse Pose (Savasana)", duration_or_reps="5 mins")
                ],
                recovery_note="Plan out your grocery list and workout schedule for the coming week."
            )
        ]

        return WorkoutPlanDataSchema(
            plan_title=f"{name}'s 7-Day Metabolic Fat Loss & Toning Engine",
            summary=f"Scientifically crafted fat-loss program combining high EPOC circuit training, steady-state cardio, and strategic recovery to maximize caloric expenditure while retaining lean tissue at {intensity} intensity.",
            target_goal=goal,
            intensity=intensity,
            days=days
        )

    def _build_endurance_plan(self, name: str, goal: str, intensity: str, weight: float) -> WorkoutPlanDataSchema:
        return self._build_wellness_plan(name, goal, intensity, weight)

    def _build_wellness_plan(self, name: str, goal: str, intensity: str, weight: float) -> WorkoutPlanDataSchema:
        dur = 35 if intensity == "Low" else 45
        days = [
            DayWorkoutSchema(
                day_number=1, day_name="Monday", workout_title="Full Body Mobility & Core Vitality",
                focus="Joint Range of Motion, Posture & Balance", duration_minutes=dur, is_rest_day=False,
                warmup=[WarmupItemSchema(exercise="Joint Circles & Dynamic Warmup", duration_or_reps="4 mins")],
                exercises=[
                    ExerciseSchema(name="Bodyweight Squats to Overhead Reach", sets=3, reps="12 reps", rest="45 sec", target_muscles="Quads, Core, Shoulders", tempo="2-1-2", notes="Focus on depth and ribcage expansion."),
                    ExerciseSchema(name="Incline Push-ups or Floor Push-ups", sets=3, reps="10 reps", rest="45 sec", target_muscles="Chest, Triceps, Core", tempo="2-0-2", notes="Keep spine neutral."),
                    ExerciseSchema(name="Bird-Dogs", sets=3, reps="10 reps/side", rest="30 sec", target_muscles="Glutes, Lower Back, Core", tempo="3-1-2", notes="Reach long rather than high."),
                    ExerciseSchema(name="Glute Bridges", sets=3, reps="15 reps", rest="30 sec", target_muscles="Glutes, Pelvic Floor", tempo="2-2-1", notes="Squeeze at top."),
                    ExerciseSchema(name="Plank Hold", sets=3, reps="30-45 sec", rest="45 sec", target_muscles="Full Core", tempo="Static", notes="Pull belly button to spine.")
                ],
                cooldown=[CooldownItemSchema(exercise="Child's Pose", duration_or_reps="60s"), CooldownItemSchema(exercise="Cobra Pose", duration_or_reps="45s")],
                recovery_note="Drink 500ml water and eat a colorful whole-food meal."
            ),
            DayWorkoutSchema(
                day_number=2, day_name="Tuesday", workout_title="Aerobic Base & Brisk Walk / Cardio",
                focus="Cardiovascular Health & Stamina", duration_minutes=35, is_rest_day=False,
                warmup=[WarmupItemSchema(exercise="Ankle and Knee Mobilization", duration_or_reps="3 mins")],
                exercises=[
                    ExerciseSchema(name="Brisk Outdoor Walk or Stationary Cycling", sets=1, reps="25 mins", rest="None", target_muscles="Cardiorespiratory System", tempo="Moderate Pace", notes="Maintain steady breathing cadence."),
                    ExerciseSchema(name="Standing Calf and Quad Stretches", sets=2, reps="30s/side", rest="30 sec", target_muscles="Lower Body", tempo="Static", notes="Relax shoulders and breathe deeply.")
                ],
                cooldown=[CooldownItemSchema(exercise="Hamstring Stretch", duration_or_reps="45s/side")],
                recovery_note="Prioritize gentle movement to counteract desk sitting."
            ),
            DayWorkoutSchema(
                day_number=3, day_name="Wednesday", workout_title="Active Rest & Gentle Yoga Flow",
                focus="Flexibility, Breathing & Stress Reduction", duration_minutes=30, is_rest_day=True,
                warmup=[WarmupItemSchema(exercise="Neck & Shoulder Rolls", duration_or_reps="3 mins")],
                exercises=[
                    ExerciseSchema(name="Sun Salutation A Flow", sets=3, reps="5 continuous rounds", rest="60 sec", target_muscles="Full Body Flexibility", tempo="Flowing with breath", notes="Synchronize movement with inhalation and exhalation."),
                    ExerciseSchema(name="Cat-Cow to Downward Dog", sets=3, reps="8 reps", rest="45 sec", target_muscles="Spine, Hamstrings", tempo="Smooth", notes="Mobilize each vertebra.")
                ],
                cooldown=[CooldownItemSchema(exercise="Corpse Pose (Savasana)", duration_or_reps="5 mins")],
                recovery_note="Take 10 minutes to meditate or practice box breathing before bed."
            ),
            DayWorkoutSchema(
                day_number=4, day_name="Thursday", workout_title="Functional Strength & Postural Balance",
                focus="Back Strength, Core Stability, Glute Activation", duration_minutes=dur, is_rest_day=False,
                warmup=[WarmupItemSchema(exercise="Torso Twists & Arm Hugs", duration_or_reps="3 mins")],
                exercises=[
                    ExerciseSchema(name="Dumbbell or Band Rows", sets=3, reps="12 reps", rest="45 sec", target_muscles="Upper Back, Rhomboids", tempo="2-1-2", notes="Strengthen postural muscles to combat slouching."),
                    ExerciseSchema(name="Step-Ups on Low Step/Stair", sets=3, reps="10 reps/leg", rest="45 sec", target_muscles="Quads, Balance", tempo="2-0-1", notes="Maintain level hips."),
                    ExerciseSchema(name="Side-Lying Clamshells", sets=3, reps="15 reps/side", rest="30 sec", target_muscles="Glute Medius, Hip Stabilizers", tempo="2-1-1", notes="Keep pelvis stacked without rolling backwards."),
                    ExerciseSchema(name="Farmer's Walk with Moderate DBs", sets=3, reps="45 sec walk", rest="45 sec", target_muscles="Grip, Core, Traps", tempo="Steady", notes="Walk tall, brace abs."),
                    ExerciseSchema(name="Deadbugs", sets=3, reps="10 reps/side", rest="30 sec", target_muscles="Deep Core", tempo="Slow", notes="Control limbs without arching lower back.")
                ],
                cooldown=[CooldownItemSchema(exercise="Chest Stretch on Doorframe", duration_or_reps="45s/side"), CooldownItemSchema(exercise="Seated Spinal Twist", duration_or_reps="45s/side")],
                recovery_note="Ensure adequate protein and healthy fats like olive oil and nuts."
            ),
            DayWorkoutSchema(
                day_number=5, day_name="Friday", workout_title="Full Body Kinetic Energy & Light Intervals",
                focus="Metabolic Wellness & Vitality", duration_minutes=dur, is_rest_day=False,
                warmup=[WarmupItemSchema(exercise="High Knees & Butt Kicks", duration_or_reps="3 mins")],
                exercises=[
                    ExerciseSchema(name="Light Kettlebell / DB Deadlifts", sets=3, reps="12 reps", rest="60 sec", target_muscles="Hamstrings, Glutes, Spine", tempo="2-1-1", notes="Keep spine long, engage core."),
                    ExerciseSchema(name="Standing Dumbbell Shoulder Press", sets=3, reps="10-12 reps", rest="45 sec", target_muscles="Shoulders", tempo="2-0-2", notes="Press smoothly without arching back."),
                    ExerciseSchema(name="Side Planks", sets=3, reps="25-30s/side", rest="30 sec", target_muscles="Obliques", tempo="Static", notes="Keep body in straight plane."),
                    ExerciseSchema(name="Bodyweight Jump / Speed Squats", sets=3, reps="12 reps", rest="45 sec", target_muscles="Quads, Calves", tempo="Explosive", notes="Soft landings to protect knees.")
                ],
                cooldown=[CooldownItemSchema(exercise="Pigeon Pose", duration_or_reps="45s/side"), CooldownItemSchema(exercise="Butterfly Stretch", duration_or_reps="60s")],
                recovery_note="Hydrate well and celebrate completing your weekday training!"
            ),
            DayWorkoutSchema(
                day_number=6, day_name="Saturday", workout_title="Recreational Movement & Family Activity",
                focus="Play, Outdoor Exploration & Unstructured Cardio", duration_minutes=45, is_rest_day=True,
                warmup=[WarmupItemSchema(exercise="Gentle Walk & Stretch", duration_or_reps="5 mins")],
                exercises=[
                    ExerciseSchema(name="Free-form Activity (Hiking, Swimming, Cycling or Sports)", sets=1, reps="40 mins", rest="None", target_muscles="Total Body Joy & Vitality", tempo="Enjoyable", notes="Move your body in nature at an enjoyable pace.")
                ],
                cooldown=[CooldownItemSchema(exercise="Full Body Stretch", duration_or_reps="5 mins")],
                recovery_note="Spend time outdoors in natural sunlight for circadian rhythm balance."
            ),
            DayWorkoutSchema(
                day_number=7, day_name="Sunday", workout_title="Mindful Restoration & Weekly Renewal",
                focus="Parasympathetic Reset & Preparation", duration_minutes=20, is_rest_day=True,
                warmup=[WarmupItemSchema(exercise="Gentle Neck and Shoulder Circles", duration_or_reps="3 mins")],
                exercises=[
                    ExerciseSchema(name="Full Body Restorative Stretching", sets=1, reps="15 mins", rest="None", target_muscles="Fascial Release", tempo="Gentle", notes="Hold each stretch for 45-60 seconds without straining."),
                    ExerciseSchema(name="Mindful Deep Breathing & Reflection", sets=1, reps="5 mins", rest="None", target_muscles="Mental Clarity", tempo="Deep & Rhythmic", notes="Inhale 4 counts, exhale 6 counts.")
                ],
                cooldown=[CooldownItemSchema(exercise="Savasana Relaxation", duration_or_reps="5 mins")],
                recovery_note="Get ready for another great week of health and vitality!"
            )
        ]

        return WorkoutPlanDataSchema(
            plan_title=f"{name}'s 7-Day Holistic Health & Vitality Blueprint",
            summary=f"A balanced, sustainable 7-day routine designed to build foundational strength, joint resilience, cardiovascular stamina, and nervous system balance at {intensity} intensity.",
            target_goal=goal,
            intensity=intensity,
            days=days
        )

    def _regenerate_heuristic_workout(self, user_info: Dict[str, Any], current_plan: Dict[str, Any], feedback: str, quick_tags: List[str]) -> WorkoutPlanDataSchema:
        feedback_lower = (feedback + " " + " ".join(quick_tags)).lower()
        base = self.generate_workout_plan(user_info)
        new_days = []

        more_cardio = "cardio" in feedback_lower or "hiit" in feedback_lower or "aerobic" in feedback_lower
        more_rest = "rest" in feedback_lower or "recovery" in feedback_lower or "tired" in feedback_lower
        lower_intensity = "reduce" in feedback_lower or "lower" in feedback_lower or "easier" in feedback_lower or "light" in feedback_lower
        shorter = "short" in feedback_lower or "30 min" in feedback_lower or "time" in feedback_lower
        more_strength = "strength" in feedback_lower or "heavy" in feedback_lower or "muscle" in feedback_lower

        for idx, d in enumerate(base.days):
            day_copy = d.model_copy(deep=True)
            
            if shorter:
                day_copy.duration_minutes = max(25, day_copy.duration_minutes - 15)
                # Keep top 3-4 exercises
                day_copy.exercises = day_copy.exercises[:3]
                for ex in day_copy.exercises:
                    ex.sets = max(2, ex.sets - 1)

            if more_rest and idx in [2, 5]: # Convert days 3 and 6 to rest days
                day_copy.is_rest_day = True
                day_copy.workout_title = "Active Recovery & Targeted Myofascial Release"
                day_copy.focus = "Restoration, Mobility & Central Nervous System Recovery"
                day_copy.duration_minutes = 25
                day_copy.exercises = [
                    ExerciseSchema(name="Gentle Walking / Low-Intensity Mobility", sets=1, reps="15 mins", rest="None", target_muscles="Cardiovascular recovery", tempo="Casual", notes="Promotes blood circulation without muscle fatigue."),
                    ExerciseSchema(name="Full Body Static Stretching", sets=1, reps="10 mins", rest="None", target_muscles="Fascial Release", tempo="Static", notes="Hold gentle stretches for 45s.")
                ]
                day_copy.recovery_note = "Rest day added per your feedback. Maximize hydration and restorative sleep."

            if more_cardio and not day_copy.is_rest_day:
                day_copy.exercises.append(
                    ExerciseSchema(name="High-Burn Cardio Finisher (HIIT or Incline Sprints)", sets=3, reps="45 sec work / 30 sec rest", rest="45 sec", target_muscles="Cardiovascular & Calorie Burn", tempo="High Output", notes="Added per your request for elevated cardio volume.")
                )
                day_copy.duration_minutes += 10

            if lower_intensity:
                day_copy.duration_minutes = max(30, day_copy.duration_minutes - 10)
                for ex in day_copy.exercises:
                    ex.sets = max(2, ex.sets - 1)
                    ex.rest = "75-90 sec"
                    ex.notes += " (Modified for lower joint stress and accessible tempo)."

            if more_strength and not day_copy.is_rest_day:
                for ex in day_copy.exercises:
                    ex.sets = min(5, ex.sets + 1)
                    ex.reps = "5-8 reps (Heavy)"
                    ex.rest = "120 sec"

            new_days.append(day_copy)

        tags_str = f" [Refinement: {', '.join(quick_tags)}]" if quick_tags else ""
        return WorkoutPlanDataSchema(
            plan_title=f"{base.plan_title} (Refined v2{tags_str})",
            summary=f"Adapted version incorporating your direct feedback: '{feedback}'. Calibrated for optimal response, customized volume, and recovery.",
            target_goal=user_info.get("goal", "General Wellness"),
            intensity=user_info.get("intensity", "Medium"),
            days=new_days
        )

    def _generate_heuristic_nutrition(self, user_info: Dict[str, Any]) -> NutritionDataSchema:
        goal = user_info.get("goal", "General Wellness")
        weight = float(user_info.get("weight", 70.0))
        intensity = user_info.get("intensity", "Medium")

        if "Loss" in goal or "Fat" in goal:
            cal_est = f"{int(weight * 24)} - {int(weight * 27)} kcal (Mild Deficit)"
            p_grams = int(weight * 2.0)
            c_grams = int(weight * 2.2)
            f_grams = int(weight * 0.7)
            macro = MacroSplitSchema(
                protein=f"{p_grams}g (35%) — High satiety & muscle preservation",
                carbohydrates=f"{c_grams}g (35%) — Complex low-glycemic fuel",
                fats=f"{f_grams}g (30%) — Healthy lipid profiles",
                calories_estimate=cal_est
            )
            tips = DailyTipsSchema(
                nutrition="Prioritize lean poultry, fish, eggs, and tofu. Eat vegetables first at each meal to maximize satiety and fiber volume.",
                hydration="Target 3.5 Liters daily. Drink a large glass of water 15 minutes before each meal.",
                recovery="Incorporate 10-minute post-workout cooldown walks to clear lactic buildup and reduce hunger spikes.",
                sleep="Aim for 8 continuous hours. Avoid blue light 60 minutes before bed to optimize growth hormone release."
            )
        elif "Muscle" in goal or "Hypertrophy" in goal:
            cal_est = f"{int(weight * 32)} - {int(weight * 36)} kcal (Hypertrophy Surplus)"
            p_grams = int(weight * 2.2)
            c_grams = int(weight * 4.0)
            f_grams = int(weight * 0.9)
            macro = MacroSplitSchema(
                protein=f"{p_grams}g (30%) — Complete essential amino acid profile",
                carbohydrates=f"{c_grams}g (45%) — High glycogen replenishment",
                fats=f"{f_grams}g (25%) — Testosterone & hormone optimization",
                calories_estimate=cal_est
            )
            tips = DailyTipsSchema(
                nutrition="Distribute protein into 4-5 servings of 35-45g. Consume 40g carbs + 25g protein within 45 mins post-workout.",
                hydration="Drink 3.5 - 4.0 Liters daily including 500ml with electrolytes during training sessions.",
                recovery="Foam roll posterior chain and perform active mobility drills on non-lifting days.",
                sleep="Prioritize 8 to 9 hours of sleep. Deep sleep stages (N3) are when 95% of natural muscle repair occurs."
            )
        else:
            cal_est = f"{int(weight * 28)} - {int(weight * 31)} kcal (Maintenance & Vitality)"
            p_grams = int(weight * 1.6)
            c_grams = int(weight * 3.0)
            f_grams = int(weight * 0.8)
            macro = MacroSplitSchema(
                protein=f"{p_grams}g (25%) — Lean protein for cellular health",
                carbohydrates=f"{c_grams}g (50%) — Whole grains, fruits, and roots",
                fats=f"{f_grams}g (25%) — Omega-3s, nuts, seeds, and avocado",
                calories_estimate=cal_est
            )
            tips = DailyTipsSchema(
                nutrition="Eat a colorful Mediterranean-style diet rich in phytonutrients, leafy greens, legumes, and lean proteins.",
                hydration="Aim for 3.0 Liters daily. Infuse with lemon or cucumber for natural mineral absorption.",
                recovery="Take a 5-minute break every 90 minutes of desk work to stretch hip flexors and decompress the spine.",
                sleep="Maintain consistent sleep and wake times (within 30 minutes) 7 days a week to stabilize circadian rhythm."
            )

        return NutritionDataSchema(
            goal=goal,
            macro_split=macro,
            daily_tips=tips,
            hydration_target=f"{max(2.8, round(weight * 0.045, 1))} - {max(3.2, round(weight * 0.052, 1))} Liters daily",
            recovery_protocols=[
                "Contrast shower (30s cold / 90s warm) after strenuous training",
                "Daily 10-minute diaphragmatic breathing or meditation session",
                "Target 8,000 to 10,000 steps daily baseline physical activity",
                "Epsom salt bath on weekends for neuromuscular relaxation"
            ],
            sleep_target="7.5 - 8.5 hours in a cool, dark room",
            disclaimer="FitBuddy provides general fitness and wellness guidance and is not a substitute for professional medical advice, clinical nutrition diagnosis, or individual therapeutic prescription."
        )

    def generate_chat_response(
        self,
        user_info: Dict[str, Any],
        current_plan: Optional[Dict[str, Any]],
        nutrition: Optional[Dict[str, Any]],
        message: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates a personalized, sports-science coaching response grounded in the
        athlete's biometrics, active workout plan, and authoritative real-time calendar date.
        """
        if not context:
            context = build_authoritative_chat_context(
                user_info=user_info,
                active_plan_dict=current_plan,
                nutrition_dict=nutrition
            )

        user_name = user_info.get("name", "Athlete")
        user_goal = user_info.get("goal", "General Wellness")
        user_intensity = user_info.get("intensity", "Medium")
        user_weight = user_info.get("weight", 70)
        user_height = user_info.get("height", 175)
        user_age = user_info.get("age", 28)
        user_gender = user_info.get("gender", "Not specified")
        user_equipment = user_info.get("equipment", "Full Gym")

        current_date_formatted = context.get("current_date_formatted", format_date_long())
        current_date_str = context.get("current_date", str(get_current_app_date()))
        current_weekday = context.get("current_weekday", "Friday")
        today_day_num = context.get("today_day_number", 1)
        today_w = context.get("today_workout") or {}
        today_is_rest = bool(context.get("today_is_rest_day"))
        today_title = today_w.get("workout_title", "Active Recovery & Rest" if today_is_rest else "Custom Session")
        today_focus = today_w.get("focus", "Mobility & Restoration" if today_is_rest else user_goal)
        today_duration = today_w.get("duration_minutes", 30 if today_is_rest else 45)
        today_recovery_note = today_w.get("recovery_note", "Hydrate well and aim for quality sleep.")

        # Format today's exercises
        today_ex_lines = []
        for ex in today_w.get("exercises", []):
            if isinstance(ex, dict):
                e_name = ex.get("name", "Exercise")
                e_sets = ex.get("sets", 3)
                e_reps = ex.get("reps", "10-12")
                e_rest = ex.get("rest", "60s")
                e_muscles = ex.get("target_muscles", "")
                e_notes = ex.get("notes", "")
                note_str = f" [Form Cue: {e_notes}]" if e_notes else ""
                today_ex_lines.append(f"- {e_name}: {e_sets} sets × {e_reps} | Rest: {e_rest} | Targets: {e_muscles}{note_str}")
        today_exercises_formatted = "\n".join(today_ex_lines) if today_ex_lines else ("(Designated Active Recovery Day — no heavy resistance exercises)" if today_is_rest else "(Exercises tailored to your session)")

        # Format weekly 7-day schedule
        weekly_sched = context.get("weekly_schedule", [])
        schedule_lines = []
        for d in weekly_sched:
            d_num = d.get("day_number", 1)
            d_name = d.get("day_name", f"Day {d_num}")
            d_title = d.get("workout_title", "Session")
            d_focus = d.get("focus", "")
            d_rest = " (Rest Day)" if d.get("is_rest_day") else ""
            schedule_lines.append(f"Day {d_num} ({d_name}): {d_title} ({d_focus}){d_rest}")
        weekly_schedule_formatted = "\n".join(schedule_lines) if schedule_lines else "No weekly plan generated yet."

        # Format completed days
        completed_days_list = context.get("completed_days", [])
        completed_days_str = f"Day {', Day '.join(map(str, completed_days_list))}" if completed_days_list else "None yet this week"

        # Format nutrition
        nutr = context.get("nutrition", {})
        macro = nutr.get("macro_split", {}) if isinstance(nutr, dict) else {}
        calories = nutr.get("calorie_estimate") or (macro.get("calories_estimate") if isinstance(macro, dict) else "N/A")
        protein = macro.get("protein", "N/A") if isinstance(macro, dict) else "N/A"
        hydration = nutr.get("hydration_target", "3.0 Liters")
        sleep = nutr.get("sleep_target", "8 hours")
        nutrition_context = f"Calories: {calories} | Protein Target: {protein} | Hydration Target: {hydration} | Sleep Target: {sleep}"

        # Conversation history
        history_str = ""
        if chat_history:
            for item in chat_history[-6:]:
                role = "Athlete" if item.get("role") == "user" else "FitBuddy Coach"
                history_str += f"{role}: {item.get('content')}\n"

        system_prompt = f"""You are FitBuddy AI Coach.
You are a contextual fitness assistant and sports scientist for the current FitBuddy user.
You MUST answer using the user's supplied profile and active plan context.
The backend-provided current date and current workout are authoritative.

Never assume today's weekday.
Never invent a workout.
Never substitute another day's workout for today's workout.
Never use an old plan when an active plan is provided.
If today's workout is provided by the backend, treat it as authoritative.
If today's workout is a rest day, clearly tell the user that today is a rest day.
If information is missing, say that the information is unavailable rather than inventing it.

============================================================
AUTHORITATIVE APPLICATION STATE (DETERMINISTIC FACTS):
- Current Calendar Date: {current_date_formatted} ({current_date_str})
- Current Weekday: {current_weekday} (Day {today_day_num} of 7)
- Timezone: Asia/Kolkata

ATHLETE PROFILE:
- Name: {user_name}
- Age: {user_age} | Weight: {user_weight}kg | Height: {user_height}cm | Gender: {user_gender}
- Primary Goal: {user_goal}
- Intensity: {user_intensity}
- Equipment Access: {user_equipment}

TODAY'S AUTHORITATIVE SCHEDULED WORKOUT ({current_weekday}, {current_date_str}):
- Status: {'ACTIVE REST / RECOVERY DAY' if today_is_rest else 'SCHEDULED TRAINING WORKOUT'}
- Workout Title: {today_title}
- Focus Area: {today_focus}
- Estimated Duration: ~{today_duration} minutes
- Exercises for Today:
{today_exercises_formatted}
- Coach Recovery Note: {today_recovery_note}

WEEKLY 7-DAY SCHEDULE OVERVIEW:
{weekly_schedule_formatted}

COMPLETED WORKOUTS THIS WEEK:
{completed_days_str}

NUTRITION & RECOVERY METRICS:
{nutrition_context}

RECENT CONVERSATION:
{history_str}

ATHLETE MESSAGE:
"{message}"
============================================================

COACHING INSTRUCTIONS:
1. Speak directly to {user_name} in an expert, motivating, and empathetic coach tone.
2. The current date is {current_weekday}, {current_date_formatted}. Always treat this date and TODAY'S SCHEDULED WORKOUT as absolute truth.
3. When answering questions about "today", "today's workout", "what should I do today", or "what am I doing today", reference TODAY'S AUTHORITATIVE WORKOUT ({today_title} on {current_weekday}).
4. When answering questions about tomorrow, yesterday, or specific days of the week (e.g. Monday, Tuesday, Sunday), retrieve that exact day from WEEKLY 7-DAY SCHEDULE OVERVIEW.
5. If today is a rest day, confirm that today is a rest day. If today is a training day, confirm the training session.
6. If asked for exercise substitutions for today's workout, suggest biomechanical alternatives specifically for the exercises scheduled for today matching their {user_equipment} setup.
7. Keep answers concise, actionable, and formatted with clean bullet points.
"""
        raw_response = self._call_gemini_api(system_prompt, self.nutrition_model or "gemini-1.5-flash")
        if raw_response and raw_response.strip():
            resp_text = raw_response.strip()
            # Factual sanity check on date
            msg_l = message.lower()
            if any(p in msg_l for p in ["today", "what is my workout", "what do i do today", "schedule today"]):
                if current_weekday.lower() != "monday" and "today is monday" in resp_text.lower():
                    logger.warning("Gemini response contained stale Monday assumption. Falling back to authoritative heuristic engine.")
                    return self._generate_heuristic_chat_response(context, message)
            return resp_text

        return self._generate_heuristic_chat_response(context, message)

    def _generate_heuristic_chat_response(
        self,
        context: Dict[str, Any],
        msg: str
    ) -> str:
        """
        Authoritative deterministic fallback engine that dynamically resolves dates,
        active workout routines, exercise swaps, and recovery guidance without hardcoded assumptions.
        """
        msg_lower = msg.lower().strip()
        user = context.get("user") or {}
        name = user.get("name", "Athlete")
        first_name = name.split()[0] if name else "Friend"
        goal = user.get("goal", "General Wellness")
        intensity = user.get("intensity", "Medium")
        weight = float(user.get("weight", 70.0))
        equipment = user.get("equipment", "Full Gym")

        active_plan = context.get("active_plan") or {}
        plan_title = active_plan.get("plan_title", f"7-Day {goal} Blueprint")
        days_data = active_plan.get("days", [])

        cur_date = get_current_app_date()
        current_date_formatted = context.get("current_date_formatted", format_date_long(cur_date))
        current_weekday = context.get("current_weekday", "Friday")
        today_w = context.get("today_workout") or {}
        today_workout = today_w
        today_is_rest = bool(context.get("today_is_rest_day"))
        nutrition = context.get("nutrition") or {}

        # Resolve query temporal intent (today, tomorrow, yesterday, specific weekday, next workout)
        query_res = resolve_query_target_day(msg, days_data, cur_date)
        intent_type = query_res.get("intent_type")
        target_date = query_res.get("target_date")
        target_weekday = query_res.get("target_weekday", current_weekday)
        target_day_num = query_res.get("target_day_number", 1)
        target_day_data = query_res.get("day_data") or today_w

        # 1. Greetings & Introductory Prompts ("hi", "hello", "hey", "who are you", "help")
        if re.match(r"^(hi|hello|hey|greetings|howdy|sup|good morning|good afternoon|good evening|yo)\b", msg_lower) or msg_lower in ["hi", "hello", "hey", "help"]:
            t_title = today_w.get("workout_title", "Active Recovery" if today_is_rest else "Workout Session")
            status_text = f"**{t_title}**" if not today_is_rest else f"**Active Recovery & Rest**"
            return (
                f"Hey {first_name}! 👋 I'm your FitBuddy AI Fitness Coach.\n\n"
                f"Today is **{current_weekday}, {current_date_formatted}**. You're scheduled for {status_text} on your **{plan_title}** ({intensity} Intensity).\n\n"
                f"Here are a few things you can ask me right now:\n"
                f"• **'What's my workout today?'** — see today's {current_weekday} session & exercises\n"
                f"• **'What do I have tomorrow?'** — preview your next scheduled day\n"
                f"• **'Can I swap an exercise?'** — get alternatives for today's lifts\n"
                f"• **'What should I eat today?'** — meal and protein guidance\n"
                f"• **'Am I supposed to rest today?'** — check recovery schedule\n\n"
                f"What would you like help with today?"
            )

        # 2. Rest Day Verification ("am i supposed to rest today", "is today a rest day", "should i rest today", "is it rest day")
        if any(p in msg_lower for p in ["supposed to rest", "is today a rest", "should i rest today", "is it rest day", "am i resting today", "rest day today"]):
            if today_is_rest:
                return (
                    f"Yes, {first_name}! Today (**{current_weekday}, {current_date_formatted}**) is scheduled as an **Active Recovery & Rest Day** for your **{goal}** program. 🧘\n\n"
                    f"• **Focus:** {today_w.get('focus', 'Mobility and tissue repair')}\n"
                    f"• **Recommended Movement:** 20–30 minute light outdoor walk (7,000–10,000 steps) and gentle stretching.\n"
                    f"• **Recovery Note:** {today_w.get('recovery_note', 'Rest days allow muscle tissue to rebuild stronger.')}\n\n"
                    f"Prioritize hydration and restful sleep today!"
                )
            else:
                # Find next scheduled rest day
                next_rest_name = "Sunday"
                for d in days_data:
                    if d.get("is_rest_day") and d.get("day_number", 0) > today_w.get("day_number", 0):
                        next_rest_name = d.get("day_name", "your upcoming rest day")
                        break
                return (
                    f"No, {first_name}! Today (**{current_weekday}, {current_date_formatted}**) is a scheduled training day: **{today_w.get('workout_title', 'Custom Session')}**.\n\n"
                    f"• **Focus:** {today_w.get('focus', goal)}\n"
                    f"• **Duration:** ~{today_w.get('duration_minutes', 45)} minutes\n"
                    f"• **Next Rest Day:** {next_rest_name}\n\n"
                    f"Let me know if you'd like to review today's exercises or need exercise modifications!"
                )

        # 3. Tomorrow's Workout ("tomorrow", "tomorrow's workout", "what do i do tomorrow", "what's tomorrow")
        if intent_type == "tomorrow" or any(p in msg_lower for p in ["tomorrow", "tomorrow's", "tomorrows"]):
            d_data = target_day_data
            if d_data:
                d_title = d_data.get("workout_title", "Session")
                d_focus = d_data.get("focus", goal)
                d_dur = d_data.get("duration_minutes", 45)
                is_rest = d_data.get("is_rest_day", False)
                target_fmt = format_date_long(target_date)

                if is_rest:
                    return (
                        f"Tomorrow is **{target_weekday}, {target_fmt}**. Your scheduled routine is **Active Recovery & Rest** for your **{goal}** plan, {first_name}! 🧘\n\n"
                        f"• **Focus:** {d_focus}\n"
                        f"• **Recommended Movement:** Light 20–30 minute walk and gentle mobility work.\n"
                        f"• **Recovery Note:** {d_data.get('recovery_note', 'Hydrate well and aim for 8 hours of sleep.')}"
                    )

                ex_lines = []
                for ex in d_data.get("exercises", [])[:5]:
                    ex_lines.append(f"• **{ex.get('name')}**: {ex.get('sets', 3)} sets × {ex.get('reps', '10-12')} (Rest: {ex.get('rest', '60s')})")
                ex_text = "\n".join(ex_lines) if ex_lines else "• Resistance exercises calibrated for your goal."

                return (
                    f"Tomorrow is **{target_weekday}, {target_fmt}**. Your scheduled workout is **{d_title}**, {first_name}! 💪\n\n"
                    f"⏱️ **Duration:** ~{d_dur} minutes | 🎯 **Focus:** {d_focus}\n\n"
                    f"**Tomorrow's Exercises:**\n"
                    f"{ex_text}\n\n"
                    f"💡 **Coach Tip:** {d_data.get('recovery_note', 'Hydrate well and fuel for performance.')}"
                )

        # 4. Yesterday's Workout ("yesterday", "yesterday's workout", "what did i have yesterday")
        if intent_type == "yesterday" or any(p in msg_lower for p in ["yesterday", "yesterday's", "yesterdays"]):
            d_data = target_day_data
            if d_data:
                d_title = d_data.get("workout_title", "Session")
                d_focus = d_data.get("focus", goal)
                d_dur = d_data.get("duration_minutes", 45)
                is_rest = d_data.get("is_rest_day", False)
                target_fmt = format_date_long(target_date)
                status_str = "an **Active Recovery Day**" if is_rest else f"**{d_title}** (~{d_dur} min, Focus: {d_focus})"
                return f"Yesterday was **{target_weekday}, {target_fmt}**. Your scheduled plan was {status_str}, {first_name}."

        # 5. Specific Weekday Queries (e.g. "what did i have on monday", "what about sunday", "what do i do on thursday")
        if intent_type == "specific_weekday":
            d_data = target_day_data
            if d_data:
                d_num = d_data.get("day_number", target_day_num)
                d_title = d_data.get("workout_title", "Session")
                d_focus = d_data.get("focus", goal)
                d_dur = d_data.get("duration_minutes", 45)
                is_rest = d_data.get("is_rest_day", False)

                if is_rest:
                    return (
                        f"On **{target_weekday} (Day {d_num})**, your scheduled plan is **Active Recovery & Rest** for your **{goal}** program, {first_name}! 🧘\n\n"
                        f"• **Focus:** {d_focus}\n"
                        f"• **Activity:** Light walking & dynamic mobility\n"
                        f"• **Recovery Note:** {d_data.get('recovery_note', 'Hydrate and recharge.')}"
                    )

                ex_lines = []
                for ex in d_data.get("exercises", [])[:5]:
                    ex_lines.append(f"• **{ex.get('name')}**: {ex.get('sets', 3)} sets × {ex.get('reps', '10-12')} (Rest: {ex.get('rest', '60s')})")
                ex_text = "\n".join(ex_lines) if ex_lines else "• Core exercises tailored to your goal."

                return (
                    f"On **{target_weekday} (Day {d_num})**, your scheduled workout is **{d_title}**, {first_name}! 🏋️\n\n"
                    f"⏱️ **Duration:** ~{d_dur} minutes | 🎯 **Focus:** {d_focus}\n\n"
                    f"**Key Exercises:**\n"
                    f"{ex_text}\n\n"
                    f"💡 **Coach Note:** {d_data.get('recovery_note', 'Prioritize clean form and controlled tempo.')}"
                )

        # 6. What exercises do I have today? ("what exercises do i have today", "today's exercises", "todays exercises", "list exercises")
        if any(p in msg_lower for p in ["exercises do i have", "today's exercises", "todays exercises", "exercises today", "list exercises", "what exercises"]):
            if today_workout and today_workout.get("exercises"):
                ex_lines = []
                for idx, ex in enumerate(today_workout.get("exercises", []), 1):
                    ex_name = ex.get("name", "Exercise")
                    sets = ex.get("sets", 3)
                    reps = ex.get("reps", "10-12")
                    rest = ex.get("rest", "60s")
                    muscles = ex.get("target_muscles", "")
                    notes = ex.get("notes", "")
                    cue = f" — *Form: {notes}*" if notes else ""
                    ex_lines.append(f"{idx}. **{ex_name}**: {sets} sets × {reps} (Rest: {rest}) [{muscles}]{cue}")
                return (
                    f"Here are the exercises scheduled for today (**{current_weekday} • {today_workout.get('workout_title')}**), {first_name}:\n\n"
                    + "\n\n".join(ex_lines)
                )
            elif today_is_rest:
                return f"Today is **{current_weekday}**, a designated **Rest & Active Recovery Day**! No heavy resistance exercises are scheduled today. Focus on light walking and mobility."

        # 7. What's Today's Workout / Plan ("today's plan", "what is my workout", "what do i do today", "schedule today", "what am i doing today", "what is my workout today")
        if any(phrase in msg_lower for phrase in ["today's plan", "today's workout", "todays workout", "workout today", "what is my workout", "what should i do today", "what am i doing today", "what's today", "todays plan", "today plan", "what do i do today", "what is today"]):
            if today_w:
                d_name = today_w.get("day_name", current_weekday)
                d_title = today_w.get("workout_title", "Custom Session")
                d_focus = today_w.get("focus", goal)
                d_duration = today_w.get("duration_minutes", 45)
                is_rest = today_w.get("is_rest_day", False)

                if is_rest:
                    return (
                        f"Today is **{current_weekday}, {current_date_formatted}** — **Active Recovery & Rest** for your **{goal}** program, {first_name}! 🧘\n\n"
                        f"• **Focus:** {d_focus}\n"
                        f"• **Recommended Movement:** 20–30 minute light outdoor walk (7,000–10,000 steps)\n"
                        f"• **Mobility:** 10 minutes of gentle spinal, hip, and ankle stretches\n"
                        f"• **Recovery Note:** {today_w.get('recovery_note', 'Hydrate and aim for 8 hours of sleep.')}\n\n"
                        f"Rest days allow muscle tissue to rebuild stronger. Let me know if you want gentle stretching tips!"
                    )

                ex_lines = []
                for ex in today_w.get("exercises", [])[:5]:
                    ex_name = ex.get("name", "Exercise")
                    sets = ex.get("sets", 3)
                    reps = ex.get("reps", "10-12")
                    rest = ex.get("rest", "60-90s")
                    ex_lines.append(f"• **{ex_name}**: {sets} sets × {reps} (Rest: {rest})")

                ex_text = "\n".join(ex_lines) if ex_lines else "• Compound and accessory exercises tailored to your goal."
                rec_note = today_w.get("recovery_note", "Hydrate well and fuel with 25–35g protein post-session.")

                return (
                    f"Today is **{current_weekday}, {current_date_formatted}**. Your scheduled workout is **{d_title}**, {first_name}! 💪\n\n"
                    f"⏱️ **Duration:** ~{d_duration} minutes | 🎯 **Focus:** {d_focus}\n\n"
                    f"**Today's Exercises:**\n"
                    f"{ex_text}\n\n"
                    f"💡 **Coach Tip:** {rec_note}\n\n"
                    f"You can log your sets directly in the interactive tracker on your Dashboard!"
                )
            return f"Today is **{current_weekday}, {current_date_formatted}**. You are on the **{plan_title}**! Check your Dashboard or Weekly Plan to start today's session."

        # 8. Exercise Substitutions / Swaps ("swap", "substitute", "replace", "alternative", "change exercise", "replace first exercise")
        if any(w in msg_lower for w in ["swap", "substitute", "substitution", "replace", "alternative", "change exercise", "different exercise"]):
            # Check for "first exercise" or "exercise 1"
            if today_w and today_w.get("exercises") and any(p in msg_lower for p in ["first exercise", "exercise 1", "1st exercise", "today's first", "first movement"]):
                first_ex = today_w["exercises"][0]
                e_name = first_ex.get("name", "First Exercise")
                e_muscles = first_ex.get("target_muscles", "Target Muscle Group")
                return (
                    f"For today's first exercise (**{e_name}** targeting {e_muscles}), here are top substitutions for your **{equipment}** setup, {first_name}:\n\n"
                    f"• **Alternative 1 (Dumbbell / Free Weight):** Dumbbell variation (3 × 10–12 reps) — provides natural joint tracking and equal bilateral loading.\n"
                    f"• **Alternative 2 (Bodyweight / Calisthenics):** Controlled tempo bodyweight regression (3 × 12–15 reps) — low joint strain with high muscular recruitment.\n"
                    f"• **Alternative 3 (Machine / Cable):** Supported cable or machine equivalent (3 × 10–12 reps) — continuous resistance curve with maximum stability."
                )

            # Specific common lift checks
            if "bench" in msg_lower or "chest press" in msg_lower:
                return f"For **Bench Press**, here are top substitutions for your **{equipment}** setup, {first_name}:\n\n• **Dumbbell Flat Bench Press:** 3 × 10–12 reps (Allows natural wrist rotation and greater range of motion)\n• **Weighted Push-Ups / Floor Press:** 3 × 12–15 reps (Zero shoulder impingement, excellent chest activation)\n• **Incline Dumbbell Press:** 3 × 10 reps (Emphasizes clavicular upper chest fibers)"
            if "squat" in msg_lower:
                return f"For **Squats**, here are excellent joint-friendly substitutions, {first_name}:\n\n• **Goblet Squats (DB/KB):** 3 × 10–12 reps (Upright torso reduces lumbar strain)\n• **Bulgarian Split Squats:** 3 × 8–10 reps per leg (High quad and glute engagement with minimal spinal load)\n• **Leg Press:** 3 × 12 reps (Stable, controlled quad stimulus)"
            if "deadlift" in msg_lower:
                return f"For **Deadlifts**, try these effective posterior-chain alternatives, {first_name}:\n\n• **Romanian Deadlifts (Dumbbells or Barbell):** 3 × 10 reps (Great hamstring & glute stretch)\n• **Barbell / DB Hip Thrusts:** 3 × 12 reps (Pure glute activation without lower back fatigue)\n• **Kettlebell Swings:** 3 × 15 reps (Explosive hip hinge conditioning)"
            if "pull" in msg_lower or "lat" in msg_lower or "chin" in msg_lower:
                return f"For **Pull-Ups / Lat Pulldowns**, here are great back alternatives, {first_name}:\n\n• **Single-Arm Dumbbell Rows:** 3 × 10–12 reps per side (Full lat stretch and contraction)\n• **Chest-Supported Incline DB Rows:** 3 × 10 reps (Isolates upper back and lats without lower back tension)\n• **Banded Lat Pulldowns:** 3 × 15 reps (Smooth resistance curve)"

            # If asking generally for today's workout substitutions
            if today_w and today_w.get("exercises"):
                swaps = []
                sample_swaps = {
                    "bench": "Dumbbell Floor Press or Push-Ups (3 × 12 reps)",
                    "squat": "Goblet Squats or Bulgarian Split Squats (3 × 10 reps)",
                    "press": "Dumbbell Arnold Press (3 × 10 reps)",
                    "row": "Single-Arm Dumbbell Row (3 × 12 reps)",
                    "curl": "Hammer Curls or Incline DB Curls (3 × 12 reps)",
                    "lunge": "Reverse Lunges or Step-Ups (3 × 10 reps)",
                    "deadlift": "Dumbbell Romanian Deadlifts (3 × 10 reps)",
                    "walk": "Stationary Bike or Elliptical (25 mins)",
                    "plank": "Deadbugs or Bird-Dogs (3 × 12 reps)"
                }
                for ex in today_w.get("exercises", [])[:3]:
                    e_name = ex.get("name", "")
                    matched_swap = "Dumbbell or Bodyweight alternative"
                    for k, v in sample_swaps.items():
                        if k in e_name.lower():
                            matched_swap = v
                            break
                    swaps.append(f"• **{e_name}** ➔ Replace with: *{matched_swap}*")
                
                swaps_text = "\n".join(swaps)
                return (
                    f"Here are exercise substitutions for today's routine (**{today_w.get('workout_title', 'Session')}** on {current_weekday}), {first_name}:\n\n"
                    f"{swaps_text}\n\n"
                    f"These preserve the same movement patterns for **{goal}** using your **{equipment}** setup!"
                )

            return f"Here are versatile exercise substitutions for your **{equipment}** setup, {first_name}:\n\n• **Chest Press:** Dumbbell Floor Press or Push-Ups (3 × 12)\n• **Squat:** Goblet Squats or Reverse Lunges (3 × 10)\n• **Pull / Row:** Single-Arm Dumbbell Row (3 × 12)\n• **Shoulder Press:** Seated Dumbbell Press (3 × 10)\n\nLet me know which specific exercise you'd like to replace!"

        # 9. Sets & Reps Count ("how many sets", "how many reps", "total sets")
        if any(w in msg_lower for w in ["how many sets", "total sets", "how many reps", "sets today"]):
            if today_w and today_w.get("exercises"):
                total_sets = sum(ex.get("sets", 3) for ex in today_w.get("exercises", []))
                num_ex = len(today_w.get("exercises", []))
                return (
                    f"Today's scheduled workout (**{today_w.get('workout_title')}** on {current_weekday}) contains **{total_sets} total working sets** across **{num_ex} exercises**, {first_name}.\n\n"
                    f"This volume is calibrated for your **{intensity} Intensity** preference to drive progressive adaptation without overtraining."
                )

        # 10. Can I do [Day X]'s workout today? / Swap days
        if "can i do" in msg_lower and ("workout today" in msg_lower or "today" in msg_lower):
            for name in WEEKDAY_NAMES:
                if name.lower() in msg_lower and name.lower() != current_weekday.lower():
                    day_num, _, req_day = resolve_day_by_weekday_name(days_data, name)
                    req_title = req_day.get("workout_title", f"{name}'s session") if req_day else f"{name}'s session"
                    return (
                        f"Yes, {first_name}! While today ({current_weekday}) is scheduled for **{today_w.get('workout_title', 'today session')}**, you can certainly do **{name}'s workout ({req_title})** today.\n\n"
                        f"• Simply select **{name} (Day {day_num})** in your Weekly Plan and track your sets.\n"
                        f"• Be sure to allow 48 hours of recovery before training the same muscle groups again later in the week!"
                    )

        # 11. User Profile & Goals ("what is my goal", "my details", "my profile", "my weight")
        if any(phrase in msg_lower for phrase in ["my goal", "my details", "my profile", "my stats", "my info", "what is my goal"]):
            return (
                f"Here are your stored FitBuddy profile details, {first_name}:\n\n"
                f"• **Name:** {name}\n"
                f"• **Primary Goal:** {goal}\n"
                f"• **Workout Intensity:** {intensity}\n"
                f"• **Weight:** {weight} kg\n"
                f"• **Equipment Access:** {equipment}\n"
                f"• **Active Program:** {plan_title}\n\n"
                f"You can update any of these metrics anytime from your Profile page."
            )

        # 12. Too Tired / Fatigue / Low Energy / Sore / Skip ("tired", "fatigue", "exhausted", "low energy", "skip", "no energy")
        if any(w in msg_lower for w in ["tired", "fatigue", "exhausted", "low energy", "skip", "no energy", "drained"]):
            return (
                f"It's completely normal to feel fatigued sometimes, {first_name}! Since today ({current_weekday}) has **{today_w.get('workout_title', 'a workout')}**, here are 2 smart options:\n\n"
                f"• **Option A (Active Recovery):** Skip the heavy weights today. Take a 20-minute easy outdoor walk and do 10 minutes of gentle foam rolling or stretching. This promotes blood flow without draining your nervous system.\n"
                f"• **Option B (Half Volume):** Perform only 2 working sets per exercise instead of 3 or 4, keeping 3 reps in reserve.\n\n"
                f"Consistency over months matters far more than forcing a single exhausted session!"
            )

        # 13. Pain / Joint Discomfort / Injury ("pain", "hurt", "knee", "back", "shoulder", "ache", "injury")
        if any(w in msg_lower for w in ["pain", "hurt", "knee", "back", "shoulder", "ache", "injury", "tweak"]):
            if "knee" in msg_lower:
                return f"For knee discomfort during leg training, {first_name}:\n\n• **Substitution:** Switch to Box Squats (sit back onto a 90° box) or Romanian Deadlifts to load hips and glutes instead of shearing the knee joint.\n• **Form Check:** Ensure your knees track outward in line with your middle toes, not caving inward.\n• **Warmup:** Do 2 sets of bodyweight glute bridges and banded side steps.\n\n*Note: If pain is sharp or persists, rest the joint and consult a physical therapist.*"
            if "back" in msg_lower or "spine" in msg_lower:
                return f"For lower back tightness or fatigue, {first_name}:\n\n• **Substitution:** Swap unsupported barbell rows for Chest-Supported Dumbbell Rows or Cable Rows.\n• **Core Bracing:** Take a deep diaphragmatic breath into your belly and brace 360° before initiating every rep.\n• **Post-Workout:** Perform 60 seconds of Cat-Cow and Child's Pose."
            return f"Safety first, {first_name}! If you're experiencing joint pain:\n\n• Stop any exercise that causes sharp or pinching discomfort immediately.\n• Swap to low-impact bodyweight or machine alternatives with full control.\n• Apply ice or gentle heat and prioritize rest.\n\n*Disclaimer: FitBuddy provides general exercise tips. Always consult a healthcare professional for persistent pain.*"

        # 14. Nutrition / Protein / Post-Workout Meals ("eat", "food", "protein", "macro", "calorie", "diet", "meal", "shake", "hunger", "nutrition", "carbs")
        if any(w in msg_lower for w in ["eat", "food", "protein", "macro", "calorie", "diet", "meal", "shake", "hunger", "nutrition", "carbs"]):
            p_target = int(weight * 2.0) if ("Muscle" in goal or "Loss" in goal) else int(weight * 1.6)
            hyd_target = nutrition.get("hydration_target", "3.0 - 3.5 Liters") if nutrition else "3.0 - 3.5 Liters"
            w_context = f"after today's **{today_w.get('workout_title', 'session')}**" if today_w else "today"
            return (
                f"Here is your personalized nutrition guide for **{goal}** {w_context}, {first_name}! 🥗\n\n"
                f"• **Daily Protein Target:** ~**{p_target}g of protein** per day (about 30–40g per meal across 3–4 meals) for muscle repair.\n"
                f"• **Post-Workout Meal Ideas (within 1-2 hours):**\n"
                f"  1. Grilled chicken breast with jasmine rice & steamed greens\n"
                f"  2. Greek yogurt (200g) with berries, honey, and a handful of almonds\n"
                f"  3. Whey/Plant protein shake with a banana and oats\n"
                f"• **Hydration:** Aim for **{hyd_target}** of water daily to maintain energy and muscle fullness."
            )

        # 15. Cardio / HIIT / Conditioning ("cardio", "hiit", "running", "treadmill", "cycling", "endurance")
        if any(w in msg_lower for w in ["cardio", "hiit", "running", "treadmill", "cycling", "endurance", "conditioning", "steps"]):
            return (
                f"Adding cardio can boost fat loss and cardiovascular health for **{goal}**, {first_name}! 🏃\n\n"
                f"• **Zone 2 Cardio (Best for Fat Loss & Recovery):** 15–20 minutes on an incline treadmill walk (speed 4.5–5.0 km/h, incline 6–10%) right after your lifting session.\n"
                f"• **HIIT (High Intensity):** 10–12 minutes of 30s sprint / 30s rest on a stationary bike or rowing machine 1–2 times per week.\n"
                f"• **Plan Adjustment:** If you'd like permanent cardio days in your routine, click 'Refine Plan' in the header!"
            )

        # 16. Rest Intervals & Timing ("how long should i rest", "how long to rest", "rest between sets", "rest time")
        if any(phrase in msg_lower for phrase in ["how long should i rest", "how long to rest", "rest between sets", "rest time", "rest period", "how much rest"]):
            return (
                f"Here are the recommended rest intervals for your **{intensity} Intensity** sessions, {first_name}: ⏱️\n\n"
                f"• **Main Compound Exercises (Squats, Bench Press, Deadlifts, Rows):** Rest **90–120 seconds** between sets so your nervous system and muscles fully recover power.\n"
                f"• **Accessory & Isolation Movements (Curls, Lateral Raises, Tricep Pushdowns):** Rest **60 seconds**.\n"
                f"• **Core & Abs:** Rest **45–60 seconds**.\n\n"
                f"Use the rest timer in your daily workout tracker to keep your pace consistent!"
            )

        # 17. Sets, Reps & Progressive Overload ("why three sets", "how many sets", "progressive overload", "reps", "tempo", "rpe")
        if any(w in msg_lower for w in ["progressive overload", "tempo", "rpe", "why 3 sets", "why three sets", "why four sets"]):
            return (
                f"Here is how your training volume is structured, {first_name}: 📈\n\n"
                f"• **Volume Strategy:** 3–4 working sets per exercise delivers optimal muscle stimulation (10–20 weekly sets per muscle group) without overtraining.\n"
                f"• **Rep Range (8–12 reps):** Maximizes time-under-tension for hypertrophy and metabolic output.\n"
                f"• **Progressive Overload:** When you can complete all prescribed sets and reps with clean form, increase the weight by 2.5–5% in your next workout!"
            )

        # 18. Missed Workout ("missed yesterday", "missed workout", "skipped yesterday", "catch up")
        if any(w in msg_lower for w in ["missed yesterday", "missed workout", "skipped yesterday", "catch up", "fell behind"]):
            return (
                f"Don't worry at all, {first_name}! Missing a workout happens to everyone. Here is the easiest way to handle it:\n\n"
                f"• **Rule #1:** Do NOT try to do two workouts in one day—that leads to excessive fatigue.\n"
                f"• **Simple Fix:** Simply do yesterday's workout today ({current_weekday}), and shift the rest of your week forward by one day.\n"
                f"• **Consistency First:** Fitness is a marathon; one missed day won't affect your long-term progress!"
            )

        # 19. Home Workout / No Equipment ("home", "no equipment", "at home", "no gym", "hotel")
        if any(w in msg_lower for w in ["home", "no equipment", "at home", "no gym", "hotel", "travel"]):
            return (
                f"You can get an effective workout anywhere without gym machines, {first_name}! 🏠\n\n"
                f"• **Upper Body:** Push-Ups (3 × 12–15), Chair Dips (3 × 12), Doorway Rows or Towel Rows (3 × 12)\n"
                f"• **Lower Body:** Bodyweight Squats or Jump Squats (3 × 15), Bulgarian Split Squats (3 × 10/leg), Walking Lunges (3 × 12)\n"
                f"• **Core:** Plank (3 × 45s), Bicycle Crunches (3 × 20)\n\n"
                f"Keep rest periods short (45–60s) to maintain high cardiovascular intensity!"
            )

        # 20. General Context-Aware Fallback
        return (
            f"Great question, {first_name}! Today is **{current_weekday}, {current_date_formatted}** on your **{plan_title}**:\n\n"
            f"• **Today's Session:** {'Active Recovery & Rest' if today_is_rest else today_w.get('workout_title', 'Scheduled Training')}\n"
            f"• **Execution:** Follow the prescribed tempo and rest intervals in your workout tracker.\n"
            f"• **Nutrition & Recovery:** Aim for your daily protein target (~{int(weight * 1.8)}g) and 8 hours of quality sleep.\n\n"
            f"Feel free to ask me for exercise form tips, food suggestions, or substitutions for any specific movement!"
        )

ai_service = AIService()

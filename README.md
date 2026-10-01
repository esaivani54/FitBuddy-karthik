# FitBuddy — AI Fitness Planning & Nutrition Platform ⚡

FitBuddy is a production-grade, AI-powered fitness planning SaaS platform that empowers users to create, track, and continuously refine personalized 7-day workout routines and goal-specific nutrition/recovery guidance powered by Google Gemini AI.

---

## 🌟 Key Product Features

- **Multi-Step Onboarding Wizard**: Guided, accessible profile setup capturing biometrics, training experience, equipment access, primary goals, and workout intensity.
- **7-Day Periodized Workout Generation**: AI-engineered schedules with warmups, compound & isolation movements, sets, repetitions, rest intervals, tempo guidance, form execution cues, cooldowns, and daily recovery directives.
- **Dedicated Daily Workout Focus & Tracker**: Focused single-day workout view featuring an integrated rest stopwatch / timer, interactive checklist, and automatic asynchronous completion logging.
- **Adaptive AI Feedback Refinement Studio**: Conversational AI regeneration engine that preserves user physiological baselines while adjusting volume, cardio, rest days, or muscle focus based on quick chips or custom prompts.
- **Immutable Plan Version History**: Plan versioning ($v_1 \rightarrow v_2 \rightarrow v_3$) with timeline navigation, change notes, and instant active plan switching.
- **Goal-Calibrated Nutrition & Recovery Hub**: Macro split breakdowns (protein, carbs, fats, calories), hydration volume recommendations, musculoskeletal recovery protocols, and sleep optimization tips.
- **Demonstration & Administration Center**: High-level platform statistics, goal distributions, generation activity stream, searchable athlete directory, and sample data seeding tools.
- **Resilient AI Engine**: Full Google Gemini 1.5 Pro and Flash integration with strict JSON output schemas, Pydantic validation, and high-fidelity fallback generation for offline reliability.

---

## 🏗️ Architecture & Technology Stack

```
                    FITBUDDY ARCHITECTURE
                             │
                             ▼
                    FastAPI ASGI Layer
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   Jinja2 SSR Frontend               REST API Endpoints
   (Vanilla HTML5/CSS3/JS)           (/api/users, /api/workouts, /api/nutrition)
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                    Service Layer
          (WorkoutService, NutritionService, AdminService)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   Google Gemini AI Engine            SQLAlchemy ORM + SQLite
   (Gemini 1.5 Pro & Flash)           (Normalized Schema & JSON Storage)
```

- **Backend**: Python 3, FastAPI, Uvicorn, SQLAlchemy, Pydantic v2
- **Frontend**: Jinja2 Templates, Semantic HTML5, Modular CSS Design System (Plus Jakarta Sans font stack, HealthTech Emerald/Slate palette), Vanilla JavaScript
- **Database**: SQLite with foreign key enforcement and cascading deletes
- **AI Models**: Google Gemini 1.5 Pro (complex workout plan generation & refinement), Google Gemini Flash (fast nutrition & recovery guidance)
- **Testing**: Pytest with in-memory SQLite isolation and mocked AI services

---

## 🚀 Quickstart & One-Command Startup

### Windows
1. **Install Requirements & Setup**:
   ```cmd
   python install.py
   ```
2. **Start Application & Auto-Open Browser**:
   ```cmd
   python start.py
   ```

### Linux
1. **Install Requirements & Setup**:
   ```bash
   python3 install_linux.py
   ```
2. **Start Application & Auto-Open Browser**:
   ```bash
   python3 start_linux.py
   ```

### macOS
1. **Install Requirements & Setup**:
   ```bash
   python3 install_mac.py
   ```
2. **Start Application & Auto-Open Browser**:
   ```bash
   python3 start_mac.py
   ```

*(Note: If `GEMINI_API_KEY` is not provided in `.env`, FitBuddy automatically uses its built-in sports science heuristic engine with zero downtime).*

---

## 🧪 Running Automated Tests

Run the full test suite with Pytest:
```bash
./venv/bin/pytest
```

All tests run against isolated in-memory databases covering schema validation, user management, workout generation, feedback versioning, nutrition protocols, and database cascading.

---

## 📖 API Documentation & Endpoints

Interactive Swagger UI documentation is available at `/docs` and ReDoc at `/redoc`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/users` | Create user profile with validation |
| `GET` | `/api/users/{id}` | Retrieve athlete profile |
| `PUT` | `/api/users/{id}` | Update athlete profile & biometrics |
| `POST` | `/api/workouts/generate` | Generate personalized 7-day routine |
| `GET` | `/api/workouts/{id}` | Retrieve specific workout plan |
| `GET` | `/api/workouts/user/{id}/active` | Retrieve current active workout plan |
| `POST` | `/api/workouts/feedback` | Regenerate plan based on user feedback |
| `POST` | `/api/workouts/activate/{id}` | Set specific plan version as active |
| `GET` | `/api/workouts/user/{id}/history` | Retrieve plan version history timeline |
| `POST` | `/api/workouts/log-day` | Log completed exercises and notes |
| `GET` | `/api/nutrition/{user_id}` | Get goal-calibrated nutrition & recovery |
| `POST` | `/api/nutrition/{user_id}/regenerate` | Recalculate nutrition guidance |
| `GET` | `/api/admin/statistics` | Retrieve system analytics & distribution |
| `POST` | `/api/admin/seed` | Populate database with sample demonstration data |

---

## 🔒 Safety & HealthTech Compliance

FitBuddy is engineered as an educational fitness planning companion. All recommendations include sensible safety constraints and medical disclaimers informing users to consult certified healthcare providers before making radical dietary or athletic training changes.

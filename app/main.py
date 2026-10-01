import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.routes.views import router as views_router
from app.routes.api_users import router as users_router
from app.routes.api_workouts import router as workouts_router
from app.routes.api_nutrition import router as nutrition_router
from app.routes.api_admin import router as admin_router
from app.routes.api_chat import router as chat_router
from app.services.admin_service import admin_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fitbuddy")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure clean database tables exist
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully.")
    yield
    logger.info("FitBuddy server shutting down.")

app = FastAPI(
    title="FitBuddy API",
    description="AI-Powered Fitness Planning & Nutrition SaaS Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directories exist
os.makedirs("app/static/css", exist_ok=True)
os.makedirs("app/static/js", exist_ok=True)
os.makedirs("app/static/images", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include Routers
app.include_router(views_router)
app.include_router(users_router)
app.include_router(workouts_router)
app.include_router(nutrition_router)
app.include_router(admin_router)
app.include_router(chat_router)

# Custom exception handler for clean error responses
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url}: {exc}", exc_info=True)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please check system logs."}
        )
    # For web views, pass down error
    from app.routes.views import templates
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"error_message": str(exc), "status_code": 500},
        status_code=500
    )

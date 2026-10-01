from app.routes.views import router as views_router
from app.routes.api_users import router as users_router
from app.routes.api_workouts import router as workouts_router
from app.routes.api_nutrition import router as nutrition_router
from app.routes.api_admin import router as admin_router
from app.routes.api_chat import router as chat_router

__all__ = [
    "views_router",
    "users_router",
    "workouts_router",
    "nutrition_router",
    "admin_router",
    "chat_router"
]

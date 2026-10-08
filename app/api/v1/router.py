from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, climate, farms, recommendations, reference, users

api_router = APIRouter()
for r in (auth.router, users.router, reference.router, farms.router, climate.router, recommendations.router, admin.router):
    api_router.include_router(r)

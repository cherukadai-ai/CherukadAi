"""Assembles the v1 API surface from platform-core module routers.

Each module owns its own router under `app.modules.<name>.api.routes`; this file
only aggregates them. No business logic here.
"""
from fastapi import APIRouter

from app.api.v1 import health
from app.modules.agents.api import routes as agents_routes
from app.modules.ai.api import routes as ai_routes
from app.modules.ai_orchestration.api import routes as ai_orchestration_routes
from app.modules.audit.api import routes as audit_routes
from app.modules.feature_wiring.api import routes as feature_wiring_routes
from app.modules.features.api import routes as features_routes
from app.modules.files.api import routes as files_routes
from app.modules.identity.api import routes as identity_routes
from app.modules.interior_design.api import routes as interior_design_routes
from app.modules.organisations.api import routes as organisations_routes
from app.modules.permissions.api import routes as permissions_routes
from app.modules.projects.api import routes as projects_routes
from app.modules.usage.api import routes as usage_routes
from app.modules.users.api import routes as users_routes
from app.modules.workflows.api import routes as workflows_routes

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(identity_routes.router)
api_router.include_router(organisations_routes.router)
api_router.include_router(users_routes.router)
api_router.include_router(permissions_routes.router)
api_router.include_router(ai_routes.router)
api_router.include_router(ai_orchestration_routes.router)
api_router.include_router(features_routes.router)
api_router.include_router(feature_wiring_routes.router)
api_router.include_router(agents_routes.router)
api_router.include_router(workflows_routes.router)
api_router.include_router(projects_routes.router)
api_router.include_router(files_routes.router)
api_router.include_router(interior_design_routes.router)
api_router.include_router(audit_routes.router)
api_router.include_router(usage_routes.router)

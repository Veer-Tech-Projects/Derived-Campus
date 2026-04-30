from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import async_engine as engine
from app.config import settings

# --- CHANGED IMPORTS ---
from app.domains.admin_portal.routers import (
    ingestion_router, 
    identity_router, 
    registry_router, 
    config_router, 
    seat_triage_router,
    audit_router,
    media_governance_router,
    course_triage_router,
    location_governance_router
)
# [UPDATE] Add admin_management_router
from app.domains.admin_auth.routers import auth_router, admin_management_router 
from app.domains.student_portal.college_filter_tool.routers import college_filter_router
from app.domains.student_auth.routers import student_auth_router
from app.domains.student_portal.student_account.routers import student_account_router

from app.domains.student_portal.student_billing.routers.student_billing_router import (
    router as student_billing_router,
)
from app.domains.student_portal.student_billing.routers.student_billing_webhook_router import (
    router as student_billing_webhook_router,
)

app = FastAPI(title=settings.PROJECT_NAME)

# --- ENTERPRISE CORS POLICY ---
origins = [
    "http://localhost:3000",      # Local Development
    "http://127.0.0.1:3000",      
    # "https://derivedcampus.com" # Future Production Domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE
    allow_headers=["*"],  # Allows all headers
)

app.include_router(ingestion_router.router)
app.include_router(identity_router.router)
app.include_router(registry_router.router)
app.include_router(config_router.router)
app.include_router(seat_triage_router.router)
app.include_router(auth_router.router)
app.include_router(media_governance_router.router)
app.include_router(course_triage_router.router)
app.include_router(location_governance_router.router)
app.include_router(admin_management_router.router)
app.include_router(audit_router.router)
app.include_router(college_filter_router.router)
app.include_router(student_auth_router.router)
app.include_router(student_account_router.router)
app.include_router(student_billing_router)
app.include_router(student_billing_webhook_router)

@app.get("/")
async def root():
    return {"message": "Derived Campus API is Online"}

@app.get("/health")
async def health_check():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "environment": settings.PROJECT_NAME}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # <--- NEW IMPORT
from sqlalchemy import text
from app.database import async_engine as engine
from app.config import settings

# --- CHANGED IMPORTS ---
from app.domains.admin_portal.routers import ingestion_router, identity_router, registry_router, config_router, seat_triage_router

app = FastAPI(title=settings.PROJECT_NAME)

# --- NEW: ENTERPRISE CORS POLICY ---
origins = [
    "http://localhost:3000",      # Local Development
    "http://127.0.0.1:3000",      # Alternative Localhost
    # "https://derivedcampus.com" # Future Production Domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE
    allow_headers=["*"],  # Allows all headers (Authorization, Content-Type)
)

app.include_router(ingestion_router.router)
app.include_router(identity_router.router)
app.include_router(registry_router.router)
app.include_router(config_router.router)
app.include_router(seat_triage_router.router)

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
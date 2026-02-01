from fastapi import FastAPI
from sqlalchemy import text
from app.database import async_engine as engine
from app.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/")
async def root():
    return {"message": "Derived Campus API is Online"}

@app.get("/health")
async def health_check():
    """
    Checks database connectivity using the engine directly.
    Does not create a full ORM session, making it lighter and safer.
    """
    try:
        # Acquire a connection from the pool directly
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        return {
            "status": "healthy", 
            "database": "connected",
            "environment": settings.PROJECT_NAME
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "database": str(e)
        }
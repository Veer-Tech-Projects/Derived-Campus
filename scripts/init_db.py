import sys
import os
import logging

# 1. Setup Paths (Same as ingest_history.py)
CURRENT_SCRIPT_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_PATH))
sys.path.append(PROJECT_ROOT)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.append(BACKEND_DIR)

from sqlalchemy import create_engine
from app.config import settings
from app.database import Base

# CRITICAL: We MUST import the models so 'Base' knows they exist!
# If we don't import this, create_all() will do nothing.
import app.models 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_db():
    logger.info("🏗️  Starting Database Construction...")
    
    # 1. Get Sync URL (Reuse logic to strip +asyncpg)
    try:
        database_url = settings.DATABASE_URL
        if "+asyncpg" in database_url:
            database_url = database_url.replace("+asyncpg", "")
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        return

    # 2. Create Engine
    engine = create_engine(database_url)

    # 3. The Magic Command: Create All Tables
    try:
        # checkfirst=True is safe; it won't break if tables exist
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database Tables Created Successfully!")
        logger.info(f"   - Created: {list(Base.metadata.tables.keys())}")
    except Exception as e:
        logger.error(f"❌ Database Creation Failed: {e}")

if __name__ == "__main__":
    init_db()
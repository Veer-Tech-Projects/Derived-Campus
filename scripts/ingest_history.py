import sys
import os
import logging

# 1. Setup Paths
CURRENT_SCRIPT_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_SCRIPT_PATH))
sys.path.append(PROJECT_ROOT)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
sys.path.append(BACKEND_DIR)

# 2. Sync Database Imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# We CANNOT import SessionLocal from app.database because it is Async
# from app.database import SessionLocal 

from ingestion.common.services.governance import IngestionGovernanceController
from ingestion.cutoff_ingestion.core.orchestrator import UniversalNotificationOrchestrator
from ingestion.cutoff_ingestion.plugins.kcet.plugin import KCETPlugin
from app.config import settings  # Assuming you have settings, otherwise use os.getenv

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sync_db():
    """
    Creates a dedicated Synchronous Connection for Ingestion Scripts.
    Converts 'postgresql+asyncpg://' -> 'postgresql://' if needed.
    """
    # Try to fetch DB URL from settings, then env, then default
    try:
        database_url = settings.DATABASE_URL
    except:
        database_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/derived_db")

    # CRITICAL: Ensure we use the Synchronous Driver (psycopg2)
    # The app likely uses 'postgresql+asyncpg://', we need 'postgresql://'
    if "+asyncpg" in database_url:
        database_url = database_url.replace("+asyncpg", "")
    
    # Create Sync Engine
    engine = create_engine(database_url)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_plugin(slug: str):
    if slug == "kcet":
        return KCETPlugin()
    raise ValueError(f"Unknown plugin slug: {slug}")

def run_bootstrap(slug: str = "kcet"):
    # Initialize the Local Sync Session Factory
    SessionLocal = get_sync_db()
    db = SessionLocal()
    
    try:
        # 1. Initialize Components
        gov = IngestionGovernanceController()
        orchestrator = UniversalNotificationOrchestrator(gov)
        plugin = get_plugin(slug)

        print(f"🚀 Starting {plugin.get_slug().upper()} Bootstrap (Universal Mode)...")

        # 2. Run History (2023-2025)
        years = [2023, 2024, 2025] 
        total_found = 0

        for year in years:
            count = orchestrator.scan(db, plugin, year)
            print(f"✅ Year {year}: Found {count} artifacts.")
            total_found += count

        print(f"\n🎉 Bootstrap Complete! Total artifacts in Air-Lock: {total_found}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_bootstrap("kcet")
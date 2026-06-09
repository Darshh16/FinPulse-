"""
FinPulse - Quick Start Guide

This script provides easy startup for the entire FinPulse system.
"""

import asyncio
import subprocess
import time
import os
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def check_environment():
    """Check if all required environment variables are set"""
    logger.info("Checking environment...")
    
    from config.settings import settings
    
    required = ['news_api_key', 'db_password']
    missing = []
    
    for attr in required:
        try:
            val = getattr(settings, attr)
            if not val or val.startswith('your_'):
                missing.append(attr)
        except:
            missing.append(attr)
    
    if missing:
        logger.error(f"Missing configuration: {missing}")
        logger.error("Please update .env file with required values")
        return False
    
    logger.info("✅ Environment configuration is valid")
    return True


def initialize_database():
    """Initialize database"""
    logger.info("Initializing database...")
    
    from src.database import init_db
    
    try:
        init_db()
        logger.info("✅ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        return False


def run_api():
    """Run FastAPI server"""
    logger.info("Starting FastAPI server...")
    logger.info("API will be available at http://localhost:8000")
    logger.info("API Docs: http://localhost:8000/docs")
    
    os.system("python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")


def run_dashboard():
    """Run Streamlit dashboard"""
    logger.info("Starting Streamlit dashboard...")
    logger.info("Dashboard will be available at http://localhost:8501")
    
    time.sleep(2)  # Give API time to start
    os.system("streamlit run src/dashboard/app.py")


def run_pipeline():
    """Run streaming pipeline"""
    logger.info("Starting streaming pipeline...")
    logger.info("This will continuously fetch and process news")
    
    time.sleep(2)  # Give API time to start
    asyncio.run(_pipeline())


async def _pipeline():
    """Async pipeline runner"""
    from src.streaming.pipeline import run_pipeline
    await run_pipeline()


def print_banner():
    """Print welcome banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║          🚀 Welcome to FinPulse 📊                   ║
    ║                                                       ║
    ║   Real-time Financial News Sentiment Pipeline        ║
    ║                                                       ║
    ║   Version 1.0.0                                      ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
    
    Choose what to run:
    
    1. FastAPI Backend (Required for dashboard)
       Command: python -m uvicorn src.api.main:app --reload
       Access: http://localhost:8000/docs
    
    2. Streamlit Dashboard (Beautiful UI)
       Command: streamlit run src/dashboard/app.py
       Access: http://localhost:8501
    
    3. Streaming Pipeline (Continuous data processing)
       Command: python src/streaming/pipeline.py
       Note: Requires API running first
    
    ⚠️  IMPORTANT: You must run API first, then other components
    
    RECOMMENDED SETUP:
    
    Terminal 1: python -m uvicorn src.api.main:app --reload
    Terminal 2: streamlit run src/dashboard/app.py
    Terminal 3 (optional): python src/streaming/pipeline.py
    
    Then open:
    - Dashboard: http://localhost:8501
    - API Docs: http://localhost:8000/docs
    """
    print(banner)


if __name__ == "__main__":
    print_banner()
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Initialize database
    if not initialize_database():
        logger.warning("⚠️  Database initialization had issues, but continuing...")
    
    # Ask user what to run
    print("\n" + "="*60)
    print("STARTUP OPTIONS")
    print("="*60)
    print("1. Run everything (API + Dashboard + Pipeline)")
    print("2. Run API only")
    print("3. Run Dashboard only")
    print("4. Run Pipeline only")
    print("5. Exit")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        logger.info("🚀 Starting all components...")
        # This requires multiple terminals, so show instructions
        print("\n" + "="*60)
        print("To run all components, open 3 terminals and run:")
        print("="*60)
        print("Terminal 1: python -m uvicorn src.api.main:app --reload")
        print("Terminal 2: streamlit run src/dashboard/app.py")
        print("Terminal 3: python src/streaming/pipeline.py")
        print("\nStarting API in this terminal...")
        run_api()
    
    elif choice == "2":
        logger.info("Starting API only...")
        run_api()
    
    elif choice == "3":
        logger.info("Starting Dashboard only...")
        run_dashboard()
    
    elif choice == "4":
        logger.info("Starting Pipeline only...")
        run_pipeline()
    
    else:
        logger.info("Exiting...")
        sys.exit(0)

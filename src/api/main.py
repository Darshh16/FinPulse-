from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from config.settings import settings
from src.api.routes import router
from src.api.ai_assistant import router as ai_router
from src.database import init_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="FinPulse API",
    description="Real-time Financial News Sentiment Pipeline API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(ai_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("Initializing FinPulse API")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": "FinPulse",
        "description": "Real-time Financial News Sentiment Pipeline",
        "version": "1.0.0",
        "endpoints": {
            "news": "/api/v1/news",
            "ticker": "/api/v1/ticker/{symbol}",
            "sentiment": "/api/v1/sentiment/{symbol}",
            "correlation": "/api/v1/correlation/{symbol}",
            "signals": "/api/v1/signals",
            "dashboard": "/api/v1/dashboard-summary"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port
    )

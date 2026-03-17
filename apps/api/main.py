"""
BPAE FastAPI Application.

Main entry point for the Business Plan Automation Engine API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from api.v1.upload import router as upload_router
from database import get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan - startup and shutdown events.
    """
    logger.info("Starting BPAE API...")
    db = get_database()
    db.create_tables()
    logger.info("Database tables initialized")
    yield
    logger.info("Shutting down BPAE API...")


app = FastAPI(
    title="BPAE - Business Plan Automation Engine",
    description="API for processing business plan templates and generating documents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)


@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        dict: Status information
    """
    return {"status": "healthy", "service": "bpae-api", "version": "0.1.0"}


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint - API information.

    Returns:
        dict: Basic API info
    """
    return {
        "name": "BPAE API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }

"""
RTO Shield & Recovery Agent - FastAPI Application
Main entry point for the backend API server.

This is the central hub that:
- Receives order data (via API calls or webhooks)
- Triggers AI agents for risk assessment and recovery
- Serves the dashboard API
- Manages the complete order lifecycle
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database.connection import init_db, close_db
from backend.database.seed import run_seed
from backend.api.orders import router as orders_router
from backend.api.agents import router as agents_router
from backend.api.dashboard import router as dashboard_router
from backend.api.webhooks import router as webhooks_router
from backend.utils.logger import logger

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    # Startup
    logger.info("🚀 Starting RTO Shield & Recovery Agent...")
    logger.info(f"   Environment: {settings.app_env}")
    logger.info(f"   LLM Provider: {settings.llm_provider}")
    logger.info(f"   LLM Model: {settings.llm_model}")

    # Initialize database
    await init_db()
    logger.info("   ✅ Database initialized")

    # Seed data (only in development)
    if settings.is_development:
        try:
            run_seed()
            logger.info("   ✅ Seed data loaded")
        except Exception as e:
            logger.warning(f"   ⚠️  Seed data: {e}")

    logger.info("   ✅ Application ready!")
    logger.info(f"   📡 API docs: {settings.backend_url}/docs")

    yield

    # Shutdown
    logger.info("🛑 Shutting down...")
    await close_db()
    logger.info("   ✅ Database connections closed")


# Create the FastAPI application
app = FastAPI(
    title="🛡️ RTO Shield & Recovery Agent",
    description=(
        "An AI-powered multi-agent system that detects high-risk COD orders "
        "before they ship and manages post-return recovery, turning RTO losses "
        "into recovered revenue.\n\n"
        "**Agents:**\n"
        "- 🛡️ **Shield Agent**: Pre-dispatch risk assessment using behavioral analysis "
        "and address intelligence\n"
        "- 🔄 **Recovery Agent**: Post-return customer re-engagement with dynamic "
        "incentives and payment link generation\n\n"
        "Built with CrewAI + Claude/GPT-4o + Razorpay + FastAPI"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",  # Streamlit
        "http://localhost:3000",  # React (if used)
        settings.frontend_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(orders_router)
app.include_router(agents_router)
app.include_router(dashboard_router)
app.include_router(webhooks_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint with system overview."""
    return {
        "name": "🛡️ RTO Shield & Recovery Agent",
        "version": "1.0.0",
        "status": "operational",
        "agents": {
            "shield_agent": "Active - Pre-dispatch risk assessment",
            "recovery_agent": "Active - Post-return revenue recovery",
        },
        "endpoints": {
            "api_docs": "/docs",
            "orders": "/api/orders/",
            "assess_order": "/api/agents/assess/{order_id}",
            "recover_order": "/api/agents/recover/{order_id}",
            "dashboard_chat": "/api/dashboard/chat",
            "analytics": "/api/dashboard/analytics/summary",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        path=str(request.url),
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.is_development else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
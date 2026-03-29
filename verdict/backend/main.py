"""Verdict API — Multi-agent adversarial AI courtroom system.

FastAPI application with middleware stack for rate limiting, request timing,
CORS, and structured health checks. Serves as the entry point for all
REST + WebSocket endpoints defined in api.routes.
"""

import logging
import os
import sys
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import router
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.request_timing import RequestTimingMiddleware
from middleware.security import SecurityMiddleware
from utils.metrics import pipeline_metrics
from utils.event_bus import pipeline_event_bus

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Track startup time for uptime reporting
_startup_time = time.monotonic()

app = FastAPI(
    title="Verdict API",
    description="Multi-agent adversarial AI courtroom for decision evaluation",
    version="1.4.0",
)

# ─── Middleware stack (order matters: outermost first) ───
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(SecurityMiddleware, max_body_size=2_097_152)  # 2 MB
app.add_middleware(
    RateLimiterMiddleware,
    rpm=int(os.getenv("RATE_LIMIT_RPM", "60")),
    burst=int(os.getenv("RATE_LIMIT_BURST", "10")),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    """Deep health check — verifies dependency readiness.

    Returns structured health status with individual checks for:
    - API status (always alive if responding)
    - Groq API key configured
    - Redis connectivity (if REDIS_URL set)
    - Session store accessibility
    - Server uptime in seconds
    """
    checks = {}

    # Check Groq API key
    groq_key = os.getenv("GROQ_API_KEY", "")
    checks["groq_api_key"] = "configured" if groq_key and len(groq_key) > 10 else "missing"

    # Check Redis if configured
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(redis_url)
            await r.ping()
            checks["redis"] = "connected"
            await r.close()
        except Exception as e:
            checks["redis"] = f"error: {str(e)[:50]}"
    else:
        checks["redis"] = "not_configured (using MemorySaver)"

    # Check session store
    from pathlib import Path
    session_dir = Path(os.getenv("SESSION_DIR", "data/sessions"))
    checks["session_store"] = "accessible" if session_dir.exists() else "missing"

    # Calculate uptime
    uptime_seconds = round(time.monotonic() - _startup_time)

    # Overall status — "alive" for backward compatibility with monitoring
    critical_ok = checks["groq_api_key"] == "configured"

    return {
        "status": "alive",
        "version": "1.4.0",
        "health": "healthy" if critical_ok else "degraded",
        "uptime_seconds": uptime_seconds,
        "checks": checks,
        "metrics": pipeline_metrics.summary(),
        "calibration": _get_calibration_summary(),
    }


def _get_calibration_summary() -> dict:
    """Get calibration status for health endpoint."""
    try:
        from utils.confidence_calibration import calibration_tracker
        summary = calibration_tracker.summary()
        return {
            "agents_tracked": len(summary.get("agents", {})),
            "recalibration_needed": summary.get("recalibration_needed", []),
        }
    except Exception:
        return {"agents_tracked": 0, "recalibration_needed": []}


@app.get("/metrics")
async def metrics():
    """Pipeline performance metrics endpoint for monitoring.

    Returns per-agent timing, success/failure counts, and event bus stats.
    """
    return {
        **pipeline_metrics.summary(),
        "event_bus": pipeline_event_bus.stats,
    }


@app.on_event("startup")
async def on_startup():
    """Application startup handler — log configuration and readiness."""
    logger.info("Verdict API starting up...")
    logger.info("CORS origins: %s", settings.cors_origins)
    logger.info("Log level: %s", settings.log_level)
    groq_configured = bool(os.getenv("GROQ_API_KEY"))
    logger.info("Groq API key: %s", "configured" if groq_configured else "MISSING")
    redis_url = os.getenv("REDIS_URL")
    logger.info("Redis: %s", redis_url[:20] + "..." if redis_url else "not configured (MemorySaver)")
    logger.info("Verdict API ready to accept requests")


@app.on_event("shutdown")
async def on_shutdown():
    """Graceful shutdown — log and clean up resources."""
    uptime = round(time.monotonic() - _startup_time)
    await pipeline_event_bus.shutdown()
    logger.info("Verdict API shutting down after %ds uptime", uptime)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.social_platform.api.routes_content import router as content_router
from app.social_platform.api.routes_feed import router as feed_router
from app.social_platform.api.routes_trust import router as trust_router
from app.social_platform.api.routes_governance import router as governance_router
from app.social_platform.admin.event_stream_inspector import router as event_stream_router
from app.social_platform.admin.feed_debugger import router as feed_debugger_router
from app.social_platform.admin.worker_dashboard import router as worker_dashboard_router
from app.social_platform.admin.event_metrics_api import router as event_metrics_router
from app.social_platform.admin.feed_policies import router as feed_policies_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("social_platform")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Social platform starting up")
    yield
    logger.info("Social platform shutting down")


app = FastAPI(
    title="Social Civic Infrastructure Engine",
    description="Deterministic event-sourced social platform with governance",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"[{request_id}] {response.status_code} ({duration:.3f}s)")
    return response


app.include_router(content_router)
app.include_router(feed_router)
app.include_router(trust_router)
app.include_router(governance_router)
app.include_router(event_stream_router)
app.include_router(feed_debugger_router)
app.include_router(worker_dashboard_router)
app.include_router(event_metrics_router)
app.include_router(feed_policies_router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "social_platform"}


@app.get("/api/status")
def api_status():
    return {
        "status": "operational",
        "service": "social_civic_infrastructure_engine",
        "version": "1.0.0",
        "routers": ["content", "feed", "trust", "governance"],
    }

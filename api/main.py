import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.health import router as health_router
from api.routes.match import router as match_router
from api.routes.metrics import router as metrics_router
from api.routes.records import router as records_router
from common.config import get_settings
from ingestion.ingest import initialize_database


settings = get_settings()
app = FastAPI(title=settings.app_name)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    try:
        initialize_database()
        app.state.startup_error = None
    except Exception as exc:  # pragma: no cover
        app.state.startup_error = str(exc)
        logger.exception("Startup database initialization failed")


app.include_router(health_router)
app.include_router(records_router)
app.include_router(match_router)
app.include_router(metrics_router)

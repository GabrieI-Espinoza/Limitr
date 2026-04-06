from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.api.routes import router
from app.core.dependencies import setup_dependencies, shutdown_dependencies
from app.core.settings import settings
from app.middleware.rate_limit import RateLimitMiddleware

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Limitr starting up")
    await setup_dependencies(app)
    logger.info("Limitr ready — proxying to %s", settings.backend_url)
    try:
        yield
    finally:
        logger.info("Limitr shutting down")
        await shutdown_dependencies(app)


app = FastAPI(lifespan=lifespan)

app.add_middleware(RateLimitMiddleware)
app.include_router(router)

if settings.prometheus_enabled:
    app.mount("/metrics", make_asgi_app())

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from app.api.routes import router
from app.core.dependencies import setup_dependencies, shutdown_dependencies
from app.core.settings import settings
from app.middleware.rate_limit import RateLimitMiddleware

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set up dependencies before the application starts
    await setup_dependencies(app)
    try:
        # Give control to the application to start handling requests
        yield
    finally:
        # Clean up dependencies when the application shuts down
        await shutdown_dependencies(app)


app = FastAPI(lifespan=lifespan)

app.add_middleware(RateLimitMiddleware)
app.include_router(router)

if settings.prometheus_enabled:
    app.mount("/metrics", make_asgi_app())

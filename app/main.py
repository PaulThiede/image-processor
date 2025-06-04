import logging

from fastapi import FastAPI
from logging import basicConfig, getLogger, info

from .routes import router
from .db import init_db
from .middleware.rate_limiter import RateLimitMiddleware

app = FastAPI()
app.add_middleware(RateLimitMiddleware, max_calls=5, period=60)
app.include_router(router)

init_db()

#logging.basicConfig(level=logging.INFO)
#logger = getLogger(__name__)
#logger.info("Docker setup")
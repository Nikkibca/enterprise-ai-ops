from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router as api_router
from app.checkpoint import get_checkpointer


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_checkpointer() as checkpointer:
        app.state.checkpointer = checkpointer
        yield


app = FastAPI(
    title="Enterprise AI Operations Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "enterprise-ai-ops",
    }

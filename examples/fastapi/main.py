import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from supabase import acreate_client

from config import settings


async def _noop_engine(client):
    """Replaced at startup once engine.py exists."""
    await asyncio.Event().wait()


# Import engine lazily so scaffold passes tests before engine.py exists.
try:
    from engine import start_engine
except ImportError:
    start_engine = _noop_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    service_client = await acreate_client(
        settings.supabase_url, settings.supabase_service_key
    )
    app.state.service_client = service_client
    engine_task = asyncio.create_task(start_engine(service_client))
    yield
    engine_task.cancel()
    try:
        await engine_task
    except asyncio.CancelledError:
        pass
    await service_client.realtime.close()


app = FastAPI(title="Realtime Rule Engine", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

from routers import auth as auth_router  # noqa: E402
app.include_router(auth_router.router)

from routers import tasks as tasks_router  # noqa: E402
app.include_router(tasks_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

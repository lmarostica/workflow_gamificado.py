import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from server.db import init_db
from server.routers import jobs, rpas, workers
from server.services.reaper import reaper_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    stop = asyncio.Event()
    task = asyncio.create_task(reaper_loop(stop))
    yield
    stop.set()
    await task


def create_app() -> FastAPI:
    app = FastAPI(
        title="Orquestrador de RPAs — SCI Único",
        description=(
            "API central que recebe requisições de execução de RPAs, "
            "enfileira e coordena a execução nos agentes Windows."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(rpas.router)
    app.include_router(jobs.router)
    app.include_router(workers.router)
    app.include_router(workers.client_router)

    @app.get("/health", tags=["operacional"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()

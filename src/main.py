from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.controllers.api import router
from src.repositories.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Wallet API", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}

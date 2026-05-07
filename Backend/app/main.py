from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.auth import router as auth_router
from .api.chat import router as chat_router
from .core.settings import settings

app = FastAPI(title="Amzur AI Chat Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(chat_router)
app.include_router(auth_router)


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}

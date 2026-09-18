"""
SLT insight.ai API.

From the backend/ folder (virtualenv activated):

    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse # Added import here

from app.config.settings import get_settings
from app.database.connection import close_mongo_connection, connect_to_mongo
from app.database.indexes import create_indexes
from app.routers import admin, auth, chat, knowledge, retrieval, settings as system_settings, users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    connect_to_mongo()
    await create_indexes()
    yield
    close_mongo_connection()


app = FastAPI(
    title="SLT insight.ai API",
    description="Internal RBAC-secured RAG chatbot backend for SLT. Retrieval is permission-filtered before any Gemini call.",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(system_settings.router)
app.include_router(knowledge.router)
app.include_router(retrieval.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    """Redirects the root URL to the API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
"""FastAPI application entry point."""

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.routers import report, value

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="TopoTools", version="1.0.0")

# allow_credentials must stay False while origins is wildcard — the two are
# mutually exclusive per the CORS spec, and this API uses no cookies/auth.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report.router)
app.include_router(value.router)
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT)), name="static")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    index = PROJECT_ROOT / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "index.html not found"}

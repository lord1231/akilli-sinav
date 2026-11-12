from pathlib import Path

from fastapi import FastAPI, HTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import auth, curriculum, exams
from app.core.config import settings
from app.db.session import engine
from app.core.rate_limit import limiter

app = FastAPI(title=settings.APP_NAME, version="0.4.0",
              description="MEB kazanımlarına dayalı yapay zekâ destekli sınav platformu.")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth.router)
app.include_router(curriculum.router)
app.include_router(exams.router)


@app.get("/health", tags=["Sistem"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "akilli-sinav-api"}


@app.get("/health/ready", tags=["Sistem"])
def readiness_check() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Veritabanına erişilemiyor.") from exc
    return {"status": "ready", "database": "connected"}


@app.get("/", tags=["Sistem"])
def root() -> dict[str, str]:
    return {"message": "Akıllı Sınav API hazır.", "docs": "/docs", "app": "/app/", "version": app.version}


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

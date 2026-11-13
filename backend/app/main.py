import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import admin, auth, curriculum, exams
from app.core.config import settings
from app.db.session import engine
from app.core.rate_limit import limiter
from app.api.routes.exams import sweep_overdue_exams
from app.services.curriculum_seed import seed_missing_curriculum

logger = logging.getLogger("uvicorn.error")


async def _sweep_loop(interval: float) -> None:
    """Süresi dolan sınavları periyodik olarak sonuçlandırır; hata döngüyü durdurmaz."""
    while True:
        await asyncio.sleep(interval)
        try:
            finished = await asyncio.to_thread(sweep_overdue_exams)
            if finished:
                logger.info("%d süresi dolan sınav otomatik sonuçlandırıldı.", finished)
        except Exception:
            logger.exception("Süresi dolan sınavların taranması başarısız oldu.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.AUTO_IMPORT_CURRICULUM:
        try:
            result = seed_missing_curriculum()
            logger.info("Müfredat kontrolü: %d dosya, %d aktarıldı, %d atlandı, %d hata.",
                        result.files, result.imported, result.skipped, len(result.errors))
        except Exception:  # veritabanı hazır değilse API yine de açılsın
            logger.exception("Müfredat otomatik yüklemesi başarısız oldu.")
    sweeper = None
    if settings.EXAM_SWEEP_INTERVAL_SECONDS > 0:
        sweeper = asyncio.create_task(_sweep_loop(settings.EXAM_SWEEP_INTERVAL_SECONDS))
    try:
        yield
    finally:
        if sweeper:
            sweeper.cancel()
            await asyncio.gather(sweeper, return_exceptions=True)


production = settings.APP_ENV.lower() == "production"
# Arayüz satır içi script/stil/işleyici kullanmaz; tests/test_deploy_assets.py bunu güvence altına alır.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
    "font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
docs_path = None if production else "/docs"
app = FastAPI(
    title=settings.APP_NAME,
    version="0.4.0",
    description="MEB kazanımlarına dayalı yapay zekâ destekli sınav platformu.",
    docs_url=docs_path,
    redoc_url=None if production else "/redoc",
    openapi_url=None if production else "/openapi.json",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth.router)
app.include_router(curriculum.router)
app.include_router(exams.router)
app.include_router(admin.router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


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
def root() -> dict[str, str | None]:
    return {"message": "Akıllı Sınav API hazır.", "docs": "/docs" if docs_path else None,
            "app": "/app/", "version": app.version}


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
if frontend_dir.exists():
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

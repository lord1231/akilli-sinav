from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="MEB kazanımlarına dayalı yapay zekâ destekli sınav platformu.",
)


@app.get("/health", tags=["Sistem"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "akilli-sinav-api"}


@app.get("/", tags=["Sistem"])
def root() -> dict[str, str]:
    return {"message": "Akıllı Sınav API hazır.", "docs": "/docs"}

"""Eksik müfredat kayıtlarını güvenli ve tekrarlanabilir biçimde tamamlar.

Ünite ve kazanım bazında eksikleri ekler; mevcut yönetici düzenlemelerini korur.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select

from app.api.routes.curriculum import CurriculumImport
from app.cli.import_curriculum import import_file
from app.db.session import SessionLocal
from app.models import Subject

logger = logging.getLogger(__name__)


@dataclass
class SeedResult:
    files: int = 0
    imported: int = 0
    skipped: int = 0
    units_added: int = 0
    outcomes_added: int = 0
    errors: list[str] = field(default_factory=list)


def locate_curriculum_directory() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        Path.cwd() / "data" / "curriculum",
        Path.cwd().parent / "data" / "curriculum",
        here.parents[2] / "data" / "curriculum",  # Docker: /app/data/curriculum
        here.parents[3] / "data" / "curriculum",  # Depo kökü
    ]
    return next((c for c in candidates if c.is_dir()), None)


def seed_missing_curriculum(directory: Path | None = None, session_factory=None) -> SeedResult:
    factory = session_factory or SessionLocal
    result = SeedResult()
    directory = directory or locate_curriculum_directory()
    if directory is None:
        result.errors.append("data/curriculum dizini bulunamadı.")
        return result
    files = sorted(Path(directory).glob("*.json"))
    if not files:
        result.errors.append("data/curriculum dizininde JSON dosyası bulunamadı.")
        return result
    for file_path in files:
        result.files += 1
        try:
            payload = CurriculumImport.model_validate_json(file_path.read_text(encoding="utf-8"))
            units, outcomes = import_file(
                file_path, session_factory=factory, preserve_existing=True
            )
            if units == 0 and outcomes == 0:
                result.skipped += 1
            else:
                result.imported += 1
            result.units_added += units
            result.outcomes_added += outcomes
        except Exception as exc:  # tek dosya hatası diğer dersleri engellemesin
            logger.exception("Müfredat dosyası yüklenemedi: %s", file_path.name)
            result.errors.append(f"{file_path.name}: {exc}")
    return result

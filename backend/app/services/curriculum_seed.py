"""Başlangıçta eksik müfredat dosyalarını güvenli ve tekrarlanabilir biçimde yükler.

Yalnızca veritabanında bulunmayan (veya hiç ünitesi olmayan) dersler içe aktarılır.
Yöneticinin sonradan düzenlediği mevcut kazanımların üzerine yazılmaz.
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func, select

from app.api.routes.curriculum import CurriculumImport
from app.cli.import_curriculum import import_file
from app.db.session import SessionLocal
from app.models import Subject, Unit

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
    for file_path in sorted(Path(directory).glob("*.json")):
        result.files += 1
        try:
            payload = CurriculumImport.model_validate_json(file_path.read_text(encoding="utf-8"))
            with factory() as db:
                subject_id = db.scalar(select(Subject.id).where(
                    Subject.grade_level == payload.grade_level,
                    Subject.name == payload.subject_name,
                    Subject.curriculum_version == payload.curriculum_version,
                ))
                unit_count = 0
                if subject_id is not None:
                    unit_count = db.scalar(select(func.count(Unit.id)).where(Unit.subject_id == subject_id)) or 0
            if unit_count > 0:
                result.skipped += 1
                continue
            units, outcomes = import_file(file_path, session_factory=factory)
            result.imported += 1
            result.units_added += units
            result.outcomes_added += outcomes
        except Exception as exc:  # tek dosya hatası diğer dersleri engellemesin
            logger.exception("Müfredat dosyası yüklenemedi: %s", file_path.name)
            result.errors.append(f"{file_path.name}: {exc}")
    return result

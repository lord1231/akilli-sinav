"""Import a reviewed, source-verified MEB curriculum JSON file."""
import argparse
from pathlib import Path

from sqlalchemy import select

from app.api.routes.curriculum import CurriculumImport
from app.db.session import SessionLocal
from app.models import LearningOutcome, Subject, Unit


def import_file(file_path: str | Path, session_factory=None, *, preserve_existing: bool = False) -> tuple[int, int]:
    payload = CurriculumImport.model_validate_json(Path(file_path).read_text(encoding="utf-8"))
    db = (session_factory or SessionLocal)()
    units_added = 0
    outcomes_added = 0
    try:
        subject = db.scalar(select(Subject).where(
            Subject.grade_level == payload.grade_level,
            Subject.name == payload.subject_name,
            Subject.curriculum_version == payload.curriculum_version,
        ))
        if subject is None:
            subject = Subject(grade_level=payload.grade_level, name=payload.subject_name,
                              curriculum_version=payload.curriculum_version)
            db.add(subject)
            db.flush()
        for unit_data in payload.units:
            unit = db.scalar(select(Unit).where(
                Unit.subject_id == subject.id, Unit.name == unit_data.name
            ))
            if unit is None:
                unit = Unit(subject_id=subject.id, name=unit_data.name, order_no=unit_data.order_no)
                db.add(unit)
                db.flush()
                units_added += 1
            else:
                unit.order_no = unit_data.order_no
            for outcome_data in unit_data.outcomes:
                outcome = db.scalar(select(LearningOutcome).where(
                    LearningOutcome.unit_id == unit.id, LearningOutcome.code == outcome_data.code
                ))
                if outcome is None:
                    outcome = LearningOutcome(
                        unit_id=unit.id, code=outcome_data.code,
                        description=outcome_data.description,
                        source_url=payload.source_url,
                        source_version=payload.curriculum_version,
                    )
                    db.add(outcome)
                    outcomes_added += 1
                elif not preserve_existing:
                    outcome.description = outcome_data.description
                    outcome.source_url = payload.source_url
                    outcome.source_version = payload.curriculum_version
                db.flush()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"{Path(file_path).name}: {units_added} yeni ünite, {outcomes_added} yeni kazanım.")
    return units_added, outcomes_added


def main() -> None:
    parser = argparse.ArgumentParser(description="MEB müfredat JSON aktarımı")
    parser.add_argument("file", help="JSON dosyasının yolu")
    args = parser.parse_args()
    import_file(args.file)


if __name__ == "__main__":
    main()

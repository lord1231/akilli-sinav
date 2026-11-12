import json
from pathlib import Path

import pytest

from app.api.routes.curriculum import CurriculumImport, validate_meb_source


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CURRICULUM_DIR = REPOSITORY_ROOT / "data" / "curriculum"
SEED_FILES = [
    "5-matematik-tymm-2024.json",
    "5-sosyal-bilgiler-tymm-2024.json",
    "5-fen-bilimleri-tymm-2024.json",
    "5-turkce-tymm-2024.json",
    "5-ingilizce-tymm-2025.json",
    "5-dkab-tymm-2026.json",
]


@pytest.mark.parametrize("filename", SEED_FILES)
def test_curriculum_seed_matches_import_schema_and_official_source(filename: str) -> None:
    path = CURRICULUM_DIR / filename
    raw = json.loads(path.read_text(encoding="utf-8"))

    payload = CurriculumImport.model_validate(raw)

    assert payload.grade_level == 5
    assert payload.subject_name.strip()
    assert payload.curriculum_version.strip()
    assert validate_meb_source(payload.source_url) == payload.source_url
    assert payload.units

    unit_names = [unit.name for unit in payload.units]
    unit_orders = [unit.order_no for unit in payload.units]
    assert len(unit_names) == len(set(unit_names)), f"{filename}: yinelenen ünite adı"
    assert len(unit_orders) == len(set(unit_orders)), f"{filename}: yinelenen ünite sırası"

    for unit in payload.units:
        codes = [outcome.code for outcome in unit.outcomes]
        assert len(codes) == len(set(codes)), (
            f"{filename}: {unit.name} içinde yinelenen öğrenme çıktısı kodu"
        )
        assert all(outcome.description.strip() for outcome in unit.outcomes)


def test_curriculum_seed_inventory_is_complete() -> None:
    present = {path.name for path in CURRICULUM_DIR.glob("5-*.json")}
    assert set(SEED_FILES).issubset(present)

import json
from pathlib import Path

import pytest

from app.api.routes.curriculum import CurriculumImport, validate_meb_source


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CURRICULUM_DIR = REPOSITORY_ROOT / "data" / "curriculum"
SEED_GRADES = {
    "4-sosyal-bilgiler-meb-2018.json": 4,
    "4-matematik-meb-2018.json": 4,
    "4-fen-bilimleri-meb-2018.json": 4,
    "4-turkce-meb-2019.json": 4,
    "4-ingilizce-meb-2018.json": 4,
    "4-dkab-meb-2018.json": 4,
    "4-insan-haklari-tymm-2024.json": 4,
    "4-trafik-guvenligi-meb-2018.json": 4,
    "4-muzik-meb-2018.json": 4,
    "4-gorsel-sanatlar-meb-2018.json": 4,
    "4-beden-egitimi-ve-oyun-meb-2018.json": 4,
    "5-muzik-tymm-2025.json": 5,
    "5-gorsel-sanatlar-tymm-2025.json": 5,
    "5-beden-egitimi-ve-spor-tymm-2025.json": 5,
    "5-bilisim-teknolojileri-ve-yazilim-tymm-2025.json": 5,
    "5-matematik-tymm-2024.json": 5,
    "5-sosyal-bilgiler-tymm-2024.json": 5,
    "5-fen-bilimleri-tymm-2024.json": 5,
    "5-turkce-tymm-2024.json": 5,
    "5-ingilizce-tymm-2025.json": 5,
    "5-dkab-tymm-2026.json": 5,
}


@pytest.mark.parametrize(("filename", "expected_grade"), SEED_GRADES.items())
def test_curriculum_seed_matches_import_schema_and_official_source(
    filename: str, expected_grade: int
) -> None:
    path = CURRICULUM_DIR / filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    payload = CurriculumImport.model_validate(raw)

    assert payload.grade_level == expected_grade
    assert payload.subject_name.strip()
    assert payload.curriculum_version.strip()
    assert validate_meb_source(payload.source_url) == payload.source_url
    assert payload.units
    if filename == "4-sosyal-bilgiler-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 33
    if filename == "4-matematik-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 71
    if filename == "4-fen-bilimleri-meb-2018.json":
        # The PDF lists 43 individually coded outcomes; its unit allocation table says 46.
        assert sum(len(unit.outcomes) for unit in payload.units) == 43
    if filename == "4-turkce-meb-2019.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 78
    if filename == "4-ingilizce-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 47
    if filename == "4-dkab-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 19
    if filename == "4-insan-haklari-tymm-2024.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 13
    if filename == "4-trafik-guvenligi-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 21
    if filename == "4-muzik-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 21
    if filename == "4-gorsel-sanatlar-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 16
    if filename == "4-beden-egitimi-ve-oyun-meb-2018.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 25
    if filename == "5-muzik-tymm-2025.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 15
    if filename == "5-gorsel-sanatlar-tymm-2025.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 10
    if filename == "5-beden-egitimi-ve-spor-tymm-2025.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 16
    if filename == "5-bilisim-teknolojileri-ve-yazilim-tymm-2025.json":
        assert sum(len(unit.outcomes) for unit in payload.units) == 24

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
    present = {path.name for path in CURRICULUM_DIR.glob("*.json")}
    assert set(SEED_GRADES).issubset(present)
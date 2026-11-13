"""Müfredat JSON dosyaları için veri kalitesi sözleşmesi (yeni dosya eklenirken otomatik denetlenir)."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import pytest

FILES = sorted((Path(__file__).resolve().parents[2] / "data" / "curriculum").glob("*.json"))
ids = [f.name for f in FILES]


@pytest.mark.parametrize("path", FILES, ids=ids)
def test_file_is_complete_and_consistent(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert int(path.name.split("-")[0]) == data["grade_level"], "dosya adındaki sınıf ile içerik uyuşmalı"
    assert data["subject_name"].strip() and data["curriculum_version"].strip()
    host = urlsplit(data["source_url"]).hostname or ""
    assert urlsplit(data["source_url"]).scheme == "https" and host.endswith("meb.gov.tr"), "kaynak resmî MEB adresi olmalı"
    assert data["units"], "en az bir ünite olmalı"
    unit_names = [u["name"].strip() for u in data["units"]]
    assert all(unit_names) and len(set(unit_names)) == len(unit_names), "ünite adları dolu ve benzersiz olmalı"
    assert sorted(u["order_no"] for u in data["units"]) == list(range(1, len(data["units"]) + 1)) or \
        len({u["order_no"] for u in data["units"]}) == len(data["units"]), "ünite sıra numaraları çakışmamalı"
    for unit in data["units"]:
        assert unit["outcomes"], f"'{unit['name']}' ünitesi boş"
        codes = [o["code"].strip() for o in unit["outcomes"]]
        assert all(codes) and len(set(codes)) == len(codes), f"'{unit['name']}' içinde tekrarlı/boş kazanım kodu"
        for outcome in unit["outcomes"]:
            desc = outcome["description"]
            assert desc == desc.strip() and "  " not in desc, f"{outcome['code']}: gereksiz boşluk"
            assert len(desc) >= 8, f"{outcome['code']}: açıklama çok kısa"


def test_both_grades_cover_core_subjects():
    names = {}
    for f in FILES:
        d = json.loads(f.read_text(encoding="utf-8"))
        names.setdefault(d["grade_level"], set()).add(d["subject_name"])
    for grade in (4, 5):
        for core in ("Türkçe", "Matematik", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce"):
            assert core in names[grade], f"{grade}. sınıfta {core} yok"

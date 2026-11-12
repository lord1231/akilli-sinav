"""Idempotently import every reviewed curriculum JSON file in data/curriculum."""
from pathlib import Path

from app.cli.import_curriculum import import_file


def find_curriculum_directory() -> Path:
    candidates = [
        Path.cwd() / "data" / "curriculum",
        Path.cwd().parent / "data" / "curriculum",
        Path(__file__).resolve().parents[3] / "data" / "curriculum",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise SystemExit("data/curriculum dizini bulunamadı.")


def main() -> None:
    directory = find_curriculum_directory()
    files = sorted(directory.glob("*.json"))
    if not files:
        raise SystemExit("Aktarılacak müfredat JSON dosyası bulunamadı.")
    total_units = 0
    total_outcomes = 0
    for file_path in files:
        units, outcomes = import_file(file_path)
        total_units += units
        total_outcomes += outcomes
    print(f"Toplam: {len(files)} dosya, {total_units} yeni ünite, {total_outcomes} yeni kazanım.")


if __name__ == "__main__":
    main()

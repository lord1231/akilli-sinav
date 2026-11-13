"""Kurulum sağlık denetimi: canlıya almadan önce her şeyin hazır olduğunu tek komutla gösterir.

Kullanım:
  python -m app.cli.doctor                       # ayar ve veritabanı denetimi
  python -m app.cli.doctor --live-gemini         # Gemini anahtarını gerçek bir istekle dener
  python -m app.cli.doctor --smtp-test ben@ornek.com   # gerçek bir test e-postası gönderir
Zorunlu bir denetim başarısızsa çıkış kodu 1'dir.
"""
import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, select, text

from app.core.config import settings as default_settings
from app.db.session import SessionLocal
from app.models import LearningOutcome, Subject, User

WEAK_KEYS = {"development-only-change-this-secret", "change-this-secret", "secret", "changeme"}


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    required: bool = True

    @property
    def icon(self) -> str:
        return "✅" if self.ok else ("❌" if self.required else "⚠️")


def _migration_check(db) -> Check:
    ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        if not ini.exists():
            return Check("Veritabanı migration'ları", True, "alembic.ini bulunamadı; atlandı.", required=False)
        head = ScriptDirectory.from_config(Config(str(ini))).get_current_head()
        current = MigrationContext.configure(db.connection()).get_current_revision()
    except Exception as exc:
        return Check("Veritabanı migration'ları", False, f"Okunamadı: {exc}")
    if current == head:
        return Check("Veritabanı migration'ları", True, f"Güncel ({head}).")
    return Check("Veritabanı migration'ları", False, f"Geride: {current or 'hiçbiri'} → {head}. `alembic upgrade head` çalıştırın.")


def run_checks(session_factory=None, cfg=None, live_gemini: bool = False, smtp_test: str | None = None) -> list[Check]:
    cfg = cfg or default_settings
    factory = session_factory or SessionLocal
    checks: list[Check] = []

    try:
        with factory() as db:
            db.execute(text("SELECT 1"))
        checks.append(Check("Veritabanı bağlantısı", True, "Bağlandı."))
        connected = True
    except Exception as exc:
        checks.append(Check("Veritabanı bağlantısı", False, f"Bağlanılamadı: {exc.__class__.__name__}. DATABASE_URL ve veritabanı servisini kontrol edin."))
        connected = False

    if connected:
        try:
            with factory() as db:
                checks.append(_migration_check(db))
        except Exception as exc:
            checks.append(Check("Veritabanı migration'ları", False, f"Okunamadı: {exc.__class__.__name__}"))
        try:
            with factory() as db:
                subjects = db.scalar(select(func.count(Subject.id)).where(Subject.is_active.is_(True))) or 0
                outcomes = db.scalar(select(func.count(LearningOutcome.id))) or 0
                grades = sorted({g for (g,) in db.execute(select(Subject.grade_level).distinct())})
                admins = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.is_active.is_(True))) or 0
            ok = subjects > 0 and outcomes > 0 and {4, 5} <= set(grades)
            checks.append(Check("Müfredat (ders ve kazanımlar)", ok,
                                f"{subjects} ders, {outcomes} kazanım, sınıflar: {grades or 'yok'}."
                                + ("" if ok else " Uygulamayı yeniden başlatın (AUTO_IMPORT_CURRICULUM=true) veya `python -m app.cli.import_all_curriculum` çalıştırın.")))
            checks.append(Check("Yönetici hesabı", admins > 0,
                                f"{admins} aktif yönetici." if admins else
                                "Yok. Sınavlar yönetici onayı olmadan yayımlanmaz. `python -m app.cli.create_admin` çalıştırın."))
        except Exception as exc:
            checks.append(Check("Veritabanı tabloları", False,
                                f"Okunamadı ({exc.__class__.__name__}). Tablolar yok olabilir: `alembic upgrade head` çalıştırın."))

    key = cfg.SECRET_KEY or ""
    strong = len(key) >= 32 and key.lower() not in WEAK_KEYS and "replace-with" not in key.lower()
    checks.append(Check("SECRET_KEY", strong, "Güçlü." if strong else "En az 32 karakterli, tahmin edilemez bir değer olmalı.",
                        required=cfg.APP_ENV.lower() == "production"))

    gemini_set = bool(cfg.GEMINI_API_KEY.strip()) and "replace-with" not in cfg.GEMINI_API_KEY.lower()
    checks.append(Check("GEMINI_API_KEY", gemini_set, f"Tanımlı (model: {cfg.GEMINI_MODEL})." if gemini_set
                        else "Tanımsız: sınav üretimi 503 hatası verir."))
    if live_gemini and gemini_set:
        try:
            from google import genai
            reply = genai.Client(api_key=cfg.GEMINI_API_KEY).models.generate_content(
                model=cfg.GEMINI_MODEL, contents="Sadece 'tamam' yaz.")
            checks.append(Check("Gemini canlı deneme", bool((reply.text or "").strip()), "Yanıt alındı."))
        except Exception as exc:
            checks.append(Check("Gemini canlı deneme", False, f"Başarısız: {exc.__class__.__name__}. Anahtarı/modeli ve ağ erişimini kontrol edin."))

    smtp_set = bool(cfg.SMTP_HOST.strip()) and bool(cfg.SMTP_FROM_EMAIL.strip())
    checks.append(Check("SMTP ayarları", smtp_set, f"{cfg.SMTP_HOST}:{cfg.SMTP_PORT}" if smtp_set
                        else "Eksik: parola sıfırlama ve veli sonuç e-postaları gitmez."))
    if smtp_test:
        if not smtp_set:
            checks.append(Check("SMTP test e-postası", False, "SMTP ayarları eksik olduğundan gönderilemedi."))
        else:
            try:
                from app.services.email import send_test_email
                send_test_email(smtp_test)
                checks.append(Check("SMTP test e-postası", True, f"{smtp_test} adresine gönderildi; gelen kutusunu kontrol edin."))
            except Exception as exc:
                checks.append(Check("SMTP test e-postası", False, f"Başarısız: {exc.__class__.__name__}: {exc}"))

    https = cfg.APP_BASE_URL.lower().startswith("https://") and "example" not in cfg.APP_BASE_URL.lower()
    checks.append(Check("APP_BASE_URL (HTTPS, gerçek alan adı)", https, cfg.APP_BASE_URL,
                        required=cfg.APP_ENV.lower() == "production"))

    proxy = bool(os.getenv("FORWARDED_ALLOW_IPS"))
    checks.append(Check("Proxy IP ayarı (FORWARDED_ALLOW_IPS)", proxy,
                        os.getenv("FORWARDED_ALLOW_IPS") if proxy else
                        "Tanımsız. Siteyi Nginx/Caddy/Cloudflare arkasında yayınlıyorsanız tüm kullanıcılar tek IP sayılır ve giriş sınırına (dakikada 5) takılır.",
                        required=False))
    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Akıllı Sınav kurulum denetimi")
    parser.add_argument("--live-gemini", action="store_true", help="Gemini anahtarını gerçek istekle dene")
    parser.add_argument("--smtp-test", metavar="E-POSTA", help="Bu adrese test e-postası gönder")
    args = parser.parse_args()
    checks = run_checks(live_gemini=args.live_gemini, smtp_test=args.smtp_test)
    width = max(len(c.name) for c in checks)
    for c in checks:
        print(f"{c.icon} {c.name.ljust(width)}  {c.detail}")
    failed = [c for c in checks if not c.ok and c.required]
    warned = [c for c in checks if not c.ok and not c.required]
    print(f"\nSonuç: {len(checks) - len(failed) - len(warned)} başarılı, {len(warned)} uyarı, {len(failed)} hata.")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()

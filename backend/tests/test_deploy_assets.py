"""Dağıtım ve güvenlik varlıkları: CSP, PWA manifesti, Caddy/Compose ve kurulum betiği."""
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.main import CONTENT_SECURITY_POLICY, app

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
INSTALL = ROOT / "scripts" / "install.sh"


# ---- CSP -------------------------------------------------------------------

def test_csp_header_is_sent_for_app_and_api_but_not_for_swagger_docs():
    c = TestClient(app)
    for path in ("/health", "/app/", "/app/app.js"):
        assert c.get(path).headers.get("content-security-policy") == CONTENT_SECURITY_POLICY, path
    docs = c.get("/docs")
    if docs.status_code == 200:  # yalnızca geliştirmede açık; Swagger satır içi script kullanır
        assert "content-security-policy" not in docs.headers


def test_csp_is_strict():
    for directive in ("default-src 'self'", "script-src 'self'", "style-src 'self'", "object-src 'none'",
                      "frame-ancestors 'none'", "base-uri 'none'"):
        assert directive in CONTENT_SECURITY_POLICY
    assert "unsafe-inline" not in CONTENT_SECURITY_POLICY and "unsafe-eval" not in CONTENT_SECURITY_POLICY


def test_frontend_is_compatible_with_the_strict_csp():
    """CSP'yi bozacak kalıplar eklenirse bu test uyarır (gerçek tarayıcı olmadan koruma)."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    js = (FRONTEND / "app.js").read_text(encoding="utf-8")
    css = (FRONTEND / "style.css").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), "satır içi <script> yasak"
    for name, text in (("index.html", html), ("app.js", js)):
        assert not re.search(r"<[a-z][^>]*\sstyle\s*=", text, re.I), f"{name}: satır içi style özniteliği yasak"
        assert not re.search(r"<[a-z][^>]*\son[a-z]+\s*=", text, re.I), f"{name}: satır içi olay işleyicisi yasak"
        assert "javascript:" not in text.lower(), f"{name}: javascript: bağlantısı yasak"
    assert not re.search(r"\beval\s*\(|new\s+Function\s*\(|setAttribute\(\s*['\"]style", js), "eval/Function/setAttribute(style) yasak"
    assert not re.search(r"@import|url\(\s*['\"]?https?:", css), "CSS dış kaynak yüklememeli"
    for tag in re.findall(r"<(?:script|link|img|iframe|source)[^>]+>", html, re.I):
        for url in re.findall(r"(?:src|href)=[\"'](https?://[^\"']+)", tag):
            pytest.fail(f"dış kaynak yüklenemez (CSP): {url}")


# ---- PWA / mobil -----------------------------------------------------------

def test_manifest_is_valid_and_icons_match_declared_sizes():
    manifest = json.loads((FRONTEND / "manifest.json").read_text(encoding="utf-8"))
    for key in ("name", "short_name", "start_url", "scope", "display", "icons", "theme_color", "background_color", "lang"):
        assert manifest.get(key), key
    assert manifest["start_url"].startswith("/app/") and manifest["scope"] == "/app/"
    assert manifest["display"] == "standalone" and manifest["lang"] == "tr"
    purposes = set()
    for icon in manifest["icons"]:
        path = FRONTEND / Path(icon["src"]).name
        assert icon["src"].startswith("/app/") and path.exists(), icon["src"]
        width, height = (int(x) for x in icon["sizes"].split("x"))
        with Image.open(path) as img:
            assert img.size == (width, height), f"{path.name}: gerçek boyut {img.size}"
        purposes.add(icon["purpose"])
    assert {"any", "maskable"} <= purposes
    assert any(i["sizes"] == "192x192" for i in manifest["icons"]) and any(i["sizes"] == "512x512" for i in manifest["icons"])


def test_index_links_manifest_and_icons_and_server_serves_them():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    for needle in ('rel="manifest" href="/app/manifest.json"', 'rel="apple-touch-icon"', 'name="theme-color"', 'name="viewport"'):
        assert needle in html, needle
    c = TestClient(app)
    r = c.get("/app/manifest.json")
    assert r.status_code == 200 and "json" in r.headers["content-type"] and r.json()["short_name"]
    assert c.get("/app/icon-192.png").headers["content-type"] == "image/png"


# ---- Compose + Caddy -------------------------------------------------------

def test_compose_defines_https_profile_and_private_api_binding():
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    caddy = compose["services"]["caddy"]
    assert caddy["profiles"] == ["https"], "Caddy yalnızca https profilinde başlamalı (mevcut kurulum bozulmasın)"
    assert "api" in caddy["depends_on"] and "80:80" in caddy["ports"] and "443:443" in caddy["ports"]
    mounts = " ".join(caddy["volumes"])
    assert "./deploy/Caddyfile:/etc/caddy/Caddyfile:ro" in mounts and "caddy_data:/data" in mounts
    assert {"caddy_data", "caddy_config"} <= set(compose["volumes"])
    assert compose["services"]["api"]["ports"] == ["${API_BIND:-0.0.0.0}:${API_PORT:-8000}:8000"]
    assert "db" in compose["services"] and compose["services"]["db"].get("ports") is None, "veritabanı dışarı açılmamalı"


def test_caddyfile_proxies_to_api_and_uses_env_domain():
    text = (ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    assert "{$DOMAIN}" in text and "reverse_proxy api:8000" in text and "redir @root /app/" in text


# ---- Kurulum betiği --------------------------------------------------------

@pytest.fixture()
def sandbox(tmp_path):
    (tmp_path / "scripts").mkdir()
    shutil.copy(INSTALL, tmp_path / "scripts" / "install.sh")
    return tmp_path


GOOD = {"NONINTERACTIVE": "1", "DOMAIN": "sinav.ornekalan.org", "ADMIN_EMAIL": "Yonetici@Ornek.com",
        "GEMINI_API_KEY": "AIzaSyTestAnahtar1234567890", "SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": "587",
        "SMTP_USERNAME": "gonderen@gmail.com", "SMTP_PASSWORD": "abcd efgh ijkl mnop",
        "SMTP_FROM_EMAIL": "gonderen@gmail.com"}


def run_install(sandbox, *args, **env):
    full = {"PATH": os.environ["PATH"], "HOME": str(sandbox), **GOOD, **env}
    full = {k: v for k, v in full.items() if v is not None}
    return subprocess.run(["bash", "scripts/install.sh", "--env-only", *args], cwd=sandbox, env=full,
                          capture_output=True, text=True, timeout=60)


def parse_env(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            k, _, v = line.partition("=")
            values[k] = v[1:-1] if v.startswith("'") and v.endswith("'") else v
    return values


def test_install_script_has_valid_bash_syntax():
    assert subprocess.run(["bash", "-n", str(INSTALL)], capture_output=True).returncode == 0


def test_installer_writes_private_env_that_passes_production_validation(sandbox):
    r = run_install(sandbox)
    assert r.returncode == 0, r.stderr + r.stdout
    env_file = sandbox / ".env"
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600, ".env yalnızca sahibi tarafından okunabilmeli"
    v = parse_env(env_file)
    assert v["DOMAIN"] == "sinav.ornekalan.org" and v["APP_BASE_URL"] == "https://sinav.ornekalan.org"
    assert v["ADMIN_EMAIL"] == "yonetici@ornek.com", "e-posta temizlenmeli"
    assert v["SMTP_PASSWORD"] == "abcdefghijklmnop", "Gmail uygulama parolasındaki boşluklar silinmeli"
    assert v["COMPOSE_PROFILES"] == "https" and v["API_BIND"] == "127.0.0.1" and v["FORWARDED_ALLOW_IPS"] == "*"
    assert len(v["SECRET_KEY"]) >= 48 and len(v["POSTGRES_PASSWORD"]) >= 24 and len(v["ADMIN_PASSWORD"]) >= 14
    assert v["SECRET_KEY"] != v["POSTGRES_PASSWORD"]
    assert v["ADMIN_PASSWORD"] in r.stdout, "yönetici parolası bir kez ekrana yazılmalı"
    assert v["SECRET_KEY"] not in r.stdout and v["POSTGRES_PASSWORD"] not in r.stdout and GOOD["GEMINI_API_KEY"] not in r.stdout

    # Üretilen .env, uygulamanın üretim doğrulamasından geçmeli (compose DATABASE_URL'yi böyle verir).
    settings = Settings(_env_file=str(env_file),
                        DATABASE_URL=f"postgresql+psycopg://{v['POSTGRES_USER']}:{v['POSTGRES_PASSWORD']}@db:5432/{v['POSTGRES_DB']}")
    assert settings.APP_ENV == "production" and settings.SMTP_HOST == "smtp.gmail.com"


def test_installer_secrets_are_random_per_run(sandbox, tmp_path_factory):
    a = parse_env((run_install(sandbox) and sandbox / ".env"))
    other = tmp_path_factory.mktemp("second")
    (other / "scripts").mkdir()
    shutil.copy(INSTALL, other / "scripts" / "install.sh")
    b = parse_env((run_install(other) and other / ".env"))
    assert a["SECRET_KEY"] != b["SECRET_KEY"] and a["POSTGRES_PASSWORD"] != b["POSTGRES_PASSWORD"]


def test_installer_never_overwrites_existing_env_without_force(sandbox):
    (sandbox / ".env").write_text("ELLE_YAZILMIS=1\n", encoding="utf-8")
    r = run_install(sandbox)
    assert r.returncode != 0 and "--force" in r.stderr
    assert (sandbox / ".env").read_text(encoding="utf-8") == "ELLE_YAZILMIS=1\n"
    r = run_install(sandbox, "--force")
    assert r.returncode == 0
    backups = list(sandbox.glob(".env.bak.*"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == "ELLE_YAZILMIS=1\n"
    assert "DOMAIN" in (sandbox / ".env").read_text(encoding="utf-8")


@pytest.mark.parametrize("override, expected", [
    ({"DOMAIN": "https://sinav.ornekalan.org"}, "Alan adı geçersiz"),
    ({"DOMAIN": "sinav.ornekalan.org/app"}, "Alan adı geçersiz"),
    ({"DOMAIN": "192.168.1.10"}, "Alan adı geçersiz"),
    ({"DOMAIN": "localhost"}, "Alan adı geçersiz"),
    ({"DOMAIN": "sinav.example"}, "Gerçek bir alan adı"),
    ({"DOMAIN": None}, "Alan adı geçersiz"),
    ({"ADMIN_EMAIL": "yonetici"}, "e-posta"),
    ({"GEMINI_API_KEY": ""}, "Gemini API anahtarı gerekli"),
    ({"SMTP_PORT": "abc"}, "SMTP portu"),
    ({"SMTP_PASSWORD": ""}, "SMTP parolası"),
    ({"SMTP_PASSWORD": "can'sikici"}, "tek tırnak"),
])
def test_installer_rejects_bad_input_and_writes_nothing(sandbox, override, expected):
    r = run_install(sandbox, **override)
    assert r.returncode != 0 and expected in r.stderr, r.stderr
    assert not (sandbox / ".env").exists(), "hatalı girdiyle yarım .env bırakılmamalı"


def test_installer_prompts_when_interactive(sandbox):
    answers = "sinav.ornekalan.org\nyonetici@ornek.com\nAIzaSyTestAnahtar1234567890\n\n\n\nparola123\n\n"
    env = {"PATH": os.environ["PATH"], "HOME": str(sandbox)}
    r = subprocess.run(["bash", "scripts/install.sh", "--env-only"], cwd=sandbox, env=env, input=answers,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr + r.stdout
    v = parse_env(sandbox / ".env")
    assert v["SMTP_HOST"] == "smtp.gmail.com" and v["SMTP_PORT"] == "587", "varsayılanlar uygulanmalı"
    assert v["SMTP_USERNAME"] == "yonetici@ornek.com" and v["SMTP_FROM_EMAIL"] == "yonetici@ornek.com"


def test_installer_uses_defaults_for_empty_optional_answers(sandbox):
    r = run_install(sandbox, SMTP_HOST="", SMTP_PORT="")
    assert r.returncode == 0, r.stderr
    v = parse_env(sandbox / ".env")
    assert v["SMTP_HOST"] == "smtp.gmail.com" and v["SMTP_PORT"] == "587"

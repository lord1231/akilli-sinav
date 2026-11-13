#!/usr/bin/env bash
# Akıllı Sınav – tek komutla kurulum (HTTPS dahil).
#
# Kullanım:   bash scripts/install.sh [--env-only] [--no-start] [--force]
#   --env-only  Yalnızca .env dosyasını yazar, Docker'a dokunmaz.
#   --no-start  .env yazılır, servisler başlatılmaz.
#   --force     Mevcut .env varsa yedekleyip yeniden yazar.
# Soruları ortam değişkenleriyle de verebilirsiniz (NONINTERACTIVE=1 ile soru sorulmaz):
#   DOMAIN, ADMIN_EMAIL, GEMINI_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_ONLY=0; NO_START=0; FORCE=0
for arg in "$@"; do
  case "$arg" in
    --env-only) ENV_ONLY=1 ;;
    --no-start) NO_START=1 ;;
    --force) FORCE=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "Bilinmeyen seçenek: $arg" >&2; exit 2 ;;
  esac
done

die() { echo "❌ $*" >&2; exit 1; }
say() { echo "▶ $*"; }

rand_alnum() {  # $1 = uzunluk
  local n="$1" out=""
  if command -v openssl >/dev/null 2>&1; then
    out=$(openssl rand -base64 $((n * 4)) | tr -dc 'A-Za-z0-9')
  else
    out=$(head -c $((n * 8)) /dev/urandom | base64 | tr -dc 'A-Za-z0-9')
  fi
  printf '%s' "${out:0:n}"
}

ask() {  # değişken, soru, gizli(0/1), varsayılan
  local var="$1" prompt="$2" secret="${3:-0}" def="${4:-}" ans=""
  if [ -n "${!var:-}" ]; then return; fi
  if [ "${NONINTERACTIVE:-0}" = "1" ]; then printf -v "$var" '%s' "$def"; return; fi
  if [ "$secret" = "1" ]; then
    read -r -s -p "$prompt: " ans; echo
  else
    read -r -p "$prompt${def:+ [$def]}: " ans
  fi
  printf -v "$var" '%s' "${ans:-$def}"
}

no_quote() {  # .env içinde tek tırnak ve satır sonu desteklenmez
  case "$2" in *"'"*|*$'\n'*|*$'\r'*) die "$1 içinde tek tırnak (') veya satır sonu olamaz." ;; esac
}

if [ -f .env ] && [ "$FORCE" != "1" ]; then
  die "Mevcut .env bulundu; üzerine yazılmadı. Yeniden oluşturmak için: bash scripts/install.sh --force (eskisi yedeklenir)."
fi

echo "=== Akıllı Sınav kurulumu ==="
ask DOMAIN "Alan adınız (örn. sinav.alanadiniz.com; DNS A kaydı bu sunucunun IP'sine bakmalı)"
ask ADMIN_EMAIL "Yönetici e-posta adresi"
ask GEMINI_API_KEY "Gemini API anahtarı (zorunlu; yazarken görünmez)" 1
ask SMTP_HOST "SMTP sunucusu" 0 "smtp.gmail.com"
ask SMTP_PORT "SMTP portu" 0 "587"
ask SMTP_USERNAME "SMTP kullanıcı adı" 0 "${ADMIN_EMAIL:-}"
ask SMTP_PASSWORD "SMTP parolası (Gmail için uygulama parolası; yazarken görünmez)" 1
ask SMTP_FROM_EMAIL "Gönderen e-posta" 0 "${SMTP_USERNAME:-$ADMIN_EMAIL}"

DOMAIN=$(printf '%s' "${DOMAIN:-}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
ADMIN_EMAIL=$(printf '%s' "${ADMIN_EMAIL:-}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
SMTP_PASSWORD=$(printf '%s' "${SMTP_PASSWORD:-}" | tr -d '[:space:]')  # Gmail uygulama parolası boşluklu gösterilir
GEMINI_API_KEY=$(printf '%s' "${GEMINI_API_KEY:-}" | tr -d '[:space:]')
SMTP_USERNAME=$(printf '%s' "${SMTP_USERNAME:-}" | tr -d '[:space:]')
SMTP_FROM_EMAIL=$(printf '%s' "${SMTP_FROM_EMAIL:-}" | tr -d '[:space:]')
SMTP_HOST=$(printf '%s' "${SMTP_HOST:-}" | tr -d '[:space:]')

[[ "$DOMAIN" =~ ^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$ ]] || die "Alan adı geçersiz: '$DOMAIN'. https:// veya / olmadan, örn. sinav.alanadiniz.com yazın."
[[ "$DOMAIN" =~ \.(example|test|invalid|local|localhost)$ ]] && die "Gerçek bir alan adı gerekli (.example/.test/.local olamaz)."
[[ "$ADMIN_EMAIL" =~ ^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$ ]] || die "Yönetici e-posta adresi geçersiz."
[[ "$SMTP_PORT" =~ ^[0-9]{1,5}$ ]] || die "SMTP portu sayı olmalı."
[ -n "$GEMINI_API_KEY" ] || die "Gemini API anahtarı gerekli (üretim ortamı onsuz açılmaz). Google AI Studio'dan alın."
[ -n "$SMTP_HOST" ] && [ -n "$SMTP_FROM_EMAIL" ] || die "SMTP sunucusu ve gönderen e-posta gerekli (parola sıfırlama ve veli bildirimleri için)."
[ -z "$SMTP_USERNAME" ] || [ -n "$SMTP_PASSWORD" ] || die "SMTP kullanıcı adı verildiyse SMTP parolası da gerekli."
for v in DOMAIN ADMIN_EMAIL GEMINI_API_KEY SMTP_HOST SMTP_USERNAME SMTP_PASSWORD SMTP_FROM_EMAIL; do no_quote "$v" "${!v}"; done

SECRET_KEY=$(rand_alnum 64)
POSTGRES_PASSWORD=$(rand_alnum 32)
ADMIN_PASSWORD="Yt-$(rand_alnum 22)"
[ "${#SECRET_KEY}" -ge 48 ] && [ "${#POSTGRES_PASSWORD}" -ge 24 ] || die "Rastgele anahtar üretilemedi (openssl veya /dev/urandom gerekli)."

if [ -f .env ]; then
  cp .env ".env.bak.$(date +%Y%m%d%H%M%S)"
  say "Eski .env yedeklendi."
fi
umask 077
cat > .env <<EOF
# Otomatik oluşturuldu: $(date -u +%Y-%m-%dT%H:%M:%SZ) (scripts/install.sh). Bu dosyayı GitHub'a yüklemeyin.
APP_NAME='Akilli Sinav API'
APP_ENV=production
APP_DEBUG=false
SECRET_KEY='${SECRET_KEY}'
ACCESS_TOKEN_EXPIRE_MINUTES=30

POSTGRES_DB=akilli_sinav
POSTGRES_USER=sinav_user
POSTGRES_PASSWORD='${POSTGRES_PASSWORD}'

# HTTPS (Caddy) ve proxy: API portu yalnızca sunucu içine açılır, gerçek kullanıcı IP'si okunur.
DOMAIN='${DOMAIN}'
COMPOSE_PROFILES=https
API_PORT=8000
API_BIND=127.0.0.1
FORWARDED_ALLOW_IPS='*'
APP_BASE_URL='https://${DOMAIN}'

GEMINI_API_KEY='${GEMINI_API_KEY}'
GEMINI_MODEL=gemini-2.5-flash

SMTP_HOST='${SMTP_HOST}'
SMTP_PORT=${SMTP_PORT}
SMTP_USERNAME='${SMTP_USERNAME}'
SMTP_PASSWORD='${SMTP_PASSWORD}'
SMTP_FROM_EMAIL='${SMTP_FROM_EMAIL}'
SMTP_USE_TLS=true

ADMIN_EMAIL='${ADMIN_EMAIL}'
ADMIN_PASSWORD='${ADMIN_PASSWORD}'
ADMIN_FULL_NAME='Sistem Yöneticisi'

AUTO_IMPORT_CURRICULUM=true
EXAM_SWEEP_INTERVAL_SECONDS=60
REUSE_REVIEWED_QUESTIONS=false
EOF
chmod 600 .env
say ".env oluşturuldu (yalnızca bu kullanıcı okuyabilir)."

if [ "$ENV_ONLY" = "1" ]; then
  echo "Yönetici parolası (bir kez gösterilir, kaydedin): ${ADMIN_PASSWORD}"
  exit 0
fi
if [ "$NO_START" = "1" ]; then
  say "Servisler başlatılmadı (--no-start). Başlatmak için: docker compose up -d --build"
  exit 0
fi

command -v docker >/dev/null 2>&1 || die "Docker kurulu değil. Kurulum: https://docs.docker.com/engine/install/"
docker compose version >/dev/null 2>&1 || die "Docker Compose eklentisi bulunamadı (docker compose)."
if command -v getent >/dev/null 2>&1 && ! getent hosts "$DOMAIN" >/dev/null 2>&1; then
  echo "⚠️  $DOMAIN şu an hiçbir IP'ye çözümlenmiyor. DNS A kaydını bu sunucunun IP'sine yönlendirin; yoksa HTTPS sertifikası alınamaz."
fi

say "Servisler derleniyor ve başlatılıyor (ilk seferde birkaç dakika sürebilir)..."
docker compose up -d --build

say "API'nin hazır olması bekleniyor..."
ready=0
for _ in $(seq 1 36); do
  if docker compose exec -T api python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=3)" >/dev/null 2>&1; then ready=1; break; fi
  sleep 5
done
[ "$ready" = "1" ] || die "API 3 dakikada hazır olmadı. Günlükler: docker compose logs --tail=80 api"

say "Yönetici hesabı oluşturuluyor..."
if docker compose exec -T api python -m app.cli.create_admin; then
  sed -i '/^ADMIN_PASSWORD=/d' .env   # parola sunucuda düz metin kalmasın
  CREATED=1
else
  CREATED=0
  echo "⚠️  Yönetici oluşturulamadı (zaten var olabilir). Ayrıntı yukarıda."
fi

say "Kurulum denetimi:"
docker compose exec -T api python -m app.cli.doctor || true

cat <<EOF

✅ Kurulum tamamlandı.
   Adres:    https://${DOMAIN}/app/
   Yönetici: ${ADMIN_EMAIL}
EOF
[ "${CREATED:-0}" = "1" ] && echo "   Parola:   ${ADMIN_PASSWORD}   (bir kez gösterilir; şimdi bir yere kaydedin ve girişten sonra değiştirmeyi düşünün)"
cat <<EOF

Sonraki adımlar:
  • Gerçek Gemini denemesi:   docker compose exec api python -m app.cli.doctor --live-gemini
  • E-posta denemesi:         docker compose exec api python -m app.cli.doctor --smtp-test ${ADMIN_EMAIL}
  • Yedekleme kurun:          docs/CANLIYA_ALMA_REHBERI.md  (Bölüm 8)
  • Sertifika alınamıyorsa:   docker compose logs --tail=50 caddy   (DNS kaydını ve 80/443 portlarını kontrol edin)
EOF

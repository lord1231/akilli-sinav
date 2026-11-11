# Akıllı Sınav

MEB müfredatına dayalı, Gemini API destekli ve mobil uyumlu sınav platformu.

## Teknoloji
- Python 3.12, FastAPI
- PostgreSQL 16, SQLAlchemy 2, Alembic
- Google Gemini API (yalnızca sunucu tarafında)
- Docker Compose
- Pytest ve GitHub Actions

## Kurulum
1. `.env.example` dosyasını `.env` olarak kopyalayın.
2. Güçlü bir `SECRET_KEY`, veritabanı parolası ve sunucu ortamında `GEMINI_API_KEY` tanımlayın.
3. `docker compose up --build` ile başlatın.
4. API belgeleri: `/docs`; sağlık kontrolü: `/health`; DB kontrolü: `/health/ready`.

## Uygulanan API
- Veli kaydı: `POST /api/auth/register`
- Giriş: `POST /api/auth/login`
- Oturum profili: `GET /api/auth/me`
- Veli öğrenci hesabı oluşturma: `POST /api/auth/students` (açık veli onayı zorunlu)
- Veli öğrencilerini listeleme: `GET /api/auth/students`
- Gemini ile 25 soru üretme: `POST /api/exams/generate`
- Sınavları listeleme/görüntüleme: `GET /api/exams`, `GET /api/exams/{id}`
- Cevap kaydetme ve teslim: `POST /api/exams/{id}/answers/{exam_question_id}`, `POST /api/exams/{id}/submit`
- Sonuç ve açıklamalar: `GET /api/exams/{id}/results`

## Test
`cd backend && pip install -r requirements.txt && pytest -q`.
GitHub Actions, Python 3.12 ile testleri çalıştırır.

## Önemli durum
Bu depo şu an backend API aşamasındadır; kullanıcı arayüzü, gerçek MEB kazanım veri aktarımı, e-posta servisi ve bulut dağıtımı henüz tamamlanmamıştır. Gemini sınav üretimi, veritabanında ilgili sınıfa ait ders/ünite/kazanım kaydı ve sunucu tarafında GEMINI_API_KEY gerektirir. Yapay zekâ soruları otomatik oluşturulsa da öğrencilere açılmadan önce öğretmen/yönetici incelemesi gerektirir.

## Güvenlik
- API anahtarlarını ve gerçek öğrenci verilerini Git'e yüklemeyin.
- Öğrenci hesaplarını yalnızca veli onayıyla oluşturun.
- Admin rolü açık kayıt endpoint'inden verilemez.
- Çocuk verileri için KVKK, veri minimizasyonu, saklama süresi ve veli hakları ayrıca işletilmelidir.
- MEB kazanımlarını resmî kaynak URL'si ve sürümüyle kaydedin; telifli soru bankalarını kopyalamayın.

# Akıllı Sınav

MEB müfredatına dayalı, Gemini API destekli ve mobil uyumlu sınav platformu.

## Teknoloji
- Python 3.12, FastAPI
- PostgreSQL 16, SQLAlchemy 2, Alembic
- Google Gemini API (yalnızca sunucu tarafında)
- Docker Compose

## Başlangıç
1. Depoyu klonlayın:
   `gh repo clone lord1231/akilli-sinav`
2. Ortam dosyasını oluşturun:
   `cp .env.example .env`
3. `.env` içinde güçlü bir `SECRET_KEY`, veritabanı bilgileri ve gerekiyorsa `GEMINI_API_KEY` tanımlayın.
4. Servisleri başlatın:
   `docker compose up --build`
5. API belgelerini açın: `http://localhost:8000/docs`
6. Sağlık kontrolü: `http://localhost:8000/health`

> Güvenlik: Gerçek API anahtarlarını, parolaları veya öğrenci kişisel verilerini GitHub'a yüklemeyin. `.env` dosyası .gitignore içindedir.

## Geliştirme durumu
İlk iskelet oluşturuldu. Sonraki aşamalar: kullanıcı/veli/öğrenci modelleri, veritabanı migration'ları, kimlik doğrulama, MEB kazanım kataloğu, Gemini ile soru üretimi ve sınav akışı.

## Proje ilkeleri
- Soru üretiminde özgün içerik ve kazanım uyumu.
- Her soru yayımlanmadan önce şema ve cevap doğrulamasından geçer.
- Müfredat sürümü ve kaynak URL'si kayıt altında tutulur.
- Çocuk verileri için veli onayı, erişim kontrolü ve KVKK ilkeleri gözetilir.

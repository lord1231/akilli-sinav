# Akıllı Sınav

MEB müfredatına dayalı, Gemini API destekli ve mobil uyumlu sınav platformu.

## Teknoloji
- Python 3.12, FastAPI
- PostgreSQL 16, SQLAlchemy 2, Alembic
- Google Gemini API (yalnızca sunucu tarafında)
- Docker Compose
- Pytest ve GitHub Actions

## Yerel/cloud kurulum
1. Depoyu çalışma ortamınıza alın.
2. `.env.example` dosyasını `.env` olarak kopyalayın.
3. `.env` içinde güçlü ve rastgele bir `SECRET_KEY` belirleyin. Gemini anahtarını yalnızca sunucu ortamındaki `GEMINI_API_KEY` alanına girin.
4. Servisleri başlatın: `docker compose up --build`
5. API belgeleri: `http://localhost:8000/docs`
6. Uygulama sağlık kontrolü: `http://localhost:8000/health`
7. PostgreSQL bağlantı kontrolü: `http://localhost:8000/health/ready`

Docker başlangıcında Alembic migration'ları otomatik uygulanır. Elle çalıştırmak için backend klasöründe `alembic upgrade head` komutu kullanılabilir.

## Test
Backend klasöründe:
```bash
pip install -r requirements.txt
pytest
```

GitHub Actions, backend testlerini Python 3.12 üzerinde otomatik çalıştırır.

## Mevcut geliştirme
- FastAPI başlangıç API'si ve sağlık uçları
- PostgreSQL bağlantı katmanı
- SQLAlchemy temel modelleri: kullanıcı, ders, ünite, kazanım, soru, sınav, sınav sorusu ve öğrenci cevabı
- Alembic migration altyapısı ve ilk şema migration'ı
- İlk API testleri ve CI iş akışı

## Sonraki aşamalar
Kimlik doğrulama ve rol yetkileri, veli-öğrenci ilişkilendirmesi, MEB kazanım kataloğu, Gemini ile doğrulanmış 25 soruluk sınav üretimi, sınav çözme ekranı, sonuç/başarı raporları ve e-posta bildirimleri.

## Güvenlik ilkeleri
- Gerçek API anahtarlarını, parolaları veya öğrenci kişisel verilerini GitHub'a yüklemeyin.
- Gemini anahtarı yalnızca backend ortam değişkeninde tutulur.
- Çocuk verileri için veri minimizasyonu, veli onayı, erişim kontrolü ve KVKK ilkeleri uygulanmalıdır.
- Yapay zekâ tarafından üretilen sorular yayımlanmadan önce kazanım, seçenek ve doğru cevap doğrulamasından geçmelidir.
- Resmî müfredat kaynakları ve sürümleri kayıt altında tutulmalı; telifli soru bankaları kopyalanmamalıdır.

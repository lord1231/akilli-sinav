# Mimari

## İlk sürüm
- Mobil uyumlu web istemcisi (ilk aşamada API dokümantasyonu ve backend).
- Python 3.12 + FastAPI.
- PostgreSQL 16.
- SQLAlchemy 2 ve Alembic.
- Gemini API, yalnızca backend üzerinden çağrılır.
- JWT tabanlı oturum; parolalar Argon2 ile hash'lenir.

## Ana modüller
1. Kimlik doğrulama ve roller: veli, öğrenci, yönetici.
2. Öğrenci profili ve veli-öğrenci ilişkisi.
3. Sınıf, ders, müfredat sürümü ve kazanımlar.
4. Soru havuzu, kaynak ve doğrulama.
5. Sınav oluşturma, öğrenci cevapları ve sonuçlar.
6. E-posta bildirimleri ve hata raporları.
7. Müfredat değişiklikleri ve prompt sürüm takibi.

## Güvenlik ilkeleri
- Gerçek API anahtarları ve parolalar Git'e eklenmez.
- Çocuk hesapları için veli onayı ve KVKK gereklilikleri tasarımın parçasıdır.
- MEB kazanımları resmî kaynak URL'si ve sürüm bilgisiyle saklanır.
- Üçüncü taraf soru içerikleri lisans ve kaynak kontrolünden geçirilir.

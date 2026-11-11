# Akıllı Sınav — MEB müfredat doğrulama yol haritası

Son inceleme: 12 Kasım 2026  
Amaç: 4. ve 5. sınıflar için program sürümünü, sınıf kapsamını ve yürürlük yılını doğrulamadan kazanım verisini etkinleştirmemek.

## Resmî kaynaklar

- TTKB öğretim programları kataloğu: https://mufredat.meb.gov.tr/Programlar.aspx
- TYMM öğretim programları: https://tymm.meb.gov.tr/ogretim-programlari
- TYMM temel eğitim taslak yıllık planları: https://tymm.meb.gov.tr/taslak-cerceve-planlari/temel-egitim
- MEB 2026-2027 e-içerik tablosu güncelleme duyurusu: https://ttkb.meb.gov.tr/www/ders-kitaplari-ve-egitim-araclari-e-icerik-tablosu-guncellendi/icerik/931/tr

## Ders bazında doğrulama durumu

Aşağıdaki liste, katalog arama görünümünde tespit edilen program adları/sınıf kapsamları ile TYMM portalında erişilebilen sınıf sayfalarının envanteridir. Katalog sayfasının önbelleğe alınmış metin görünümü bazı eski sürümleri de göstermektedir. Bu nedenle burada listelenen bir program, PDF/kurul kararı/yürürlük takvimi ayrıca doğrulanmadan otomatik olarak etkin kabul edilmez.

| Sınıf | Ders | Katalogda görünen program | Sistemdeki durum |
|---|---|---|---|
| 4 | Türkçe | İlkokul Türkçe (1-4), 2026 kaydı katalog görünümünde | Yeni sürümün PDF/karar doğrulaması bekliyor |
| 4 | Matematik | İlkokul Matematik (1-4), 2026 kaydı katalog görünümünde | Yeni sürümün PDF/karar doğrulaması bekliyor |
| 4 | Fen Bilimleri | Fen Bilimleri (3-8), 2026 kaydı katalog görünümünde | Yeni sürümün PDF/karar doğrulaması bekliyor |
| 4 | Sosyal Bilgiler | Sosyal Bilgiler (4-7), 2026 kaydı katalog görünümünde | Yeni sürümün PDF/karar doğrulaması bekliyor |
| 4 | İngilizce | İngilizce (2-8), 2025 | Sınıf bazlı yürürlük ve kapsam kontrolü bekliyor |
| 4 | İnsan Hakları, Vatandaşlık ve Demokrasi | 4. sınıf, 2024 | Ders bazlı program ve yürürlük kontrolü gerekli |
| 4 | Trafik Güvenliği | 4. sınıf, 2025 | Ders bazlı program ve yürürlük kontrolü gerekli |
| 4 | Din Kültürü ve Ahlak Bilgisi | 4-8, 2026 | 4. sınıfta 2027-2028'de uygulanacak; 2026-2027 için yeni program etkinleştirilmez |
| 5 | Matematik | Ortaokul Matematik (5-8), 2026 kaydı katalog görünümünde | PDF/kurul kararı doğrulaması bekliyor |
| 5 | Türkçe | Ortaokul Türkçe (5-8), 2026 kaydı katalog görünümünde | PDF/kurul kararı doğrulaması bekliyor |
| 5 | Fen Bilimleri | Fen Bilimleri (3-8), 2026 kaydı katalog görünümünde | PDF/kurul kararı doğrulaması bekliyor |
| 5 | Sosyal Bilgiler | Sosyal Bilgiler (4-7), 2026 kaydı katalog görünümünde | PDF/kurul kararı doğrulaması bekliyor |
| 5 | İngilizce | İngilizce (2-8), 2025 | Sınıf bazlı yürürlük ve kapsam kontrolü bekliyor |
| 5 | Din Kültürü ve Ahlak Bilgisi | 4-8, 2026 | 2026-2027'de 5. sınıfta uygulanacak; program PDF'si ayrıca eşleştirilmeli |

## Portalda görülen sınıf sayfaları

- 4. sınıf İlkokul Türkçe: https://tymm.meb.gov.tr/ilkokul-turkce-dersi/unite/401
- 4. sınıf Sosyal Bilgiler: https://tymm.meb.gov.tr/ogretim-programlari/sosyal-bilgiler-dersi/5
- 5. sınıf Matematik: https://tymm.meb.gov.tr/ogretim-programlari/ortaokul-matematik-dersi/6
- 5. sınıf Türkçe: https://tymm.meb.gov.tr/ogretim-programlari/ortaokul-turkce-dersi/6
- 5. sınıf Fen Bilimleri: https://tymm.meb.gov.tr/ogretim-programlari/fen-bilimleri-dersi/6
- 5. sınıf Sosyal Bilgiler: https://tymm.meb.gov.tr/ogretim-programlari/sosyal-bilgiler-dersi/6

## Uygulama kuralları

1. Katalogda görünmek, bir sınıf seviyesinde o öğretim yılında yürürlükte olmakla aynı şey değildir.
2. 2026 katalog kaydı ile 2024/2025 tarihli portal sayfası veya PDF arasında sürüm uyuşmazlığı varsa veri aktarımı durdurulur.
3. Her ders için kurul karar tarihi, uygulama başlangıç yılı, sınıf kapsamı, PDF/program URL'si ve program sürümü birlikte doğrulanır.
4. Eski JSON dosyaları tarihsel kayıt olarak korunur. Yeni sürüm ayrı dosyaya aktarılır; eski dosyanın üstüne yazılmaz.
5. Bir dersin yalnızca tema/ünite adları görülebiliyorsa, kazanım kodları ve açıklamaları doğrulanmış sayılmaz.
6. Soru üretimi yalnızca doğrulanmış ve ilgili sınıfta yürürlükte olan kazanımlarla yapılır.

## Mevcut veri dosyaları

- `data/curriculum/5-matematik-tymm-2024.json`: tarihsel 2024 sürümü; 6 tema, 23 öğrenme çıktısı.
- `data/curriculum/5-sosyal-bilgiler-tymm-2024.json`: tarihsel 2024 sürümü; 6 öğrenme alanı, 19 öğrenme çıktısı.

Bu iki dosya silinmeyecek veya yeni programmış gibi yeniden adlandırılmayacaktır. Yeni program PDF'si ve yürürlük kararı doğrulandığında ayrı sürüm dosyaları eklenecektir.

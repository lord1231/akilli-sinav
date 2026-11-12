# Akıllı Sınav — MEB müfredat doğrulama yol haritası

Son inceleme: 12 Kasım 2026
Amaç: 4. ve 5. sınıflar için program sürümünü, sınıf kapsamını ve yürürlük yılını doğrulamadan kazanım verisini etkinleştirmemek.

## 2026-2027 uygulama ilkesi

MEB'in 2026-2027 duyurusuna göre TYMM'nin genel uygulama kapsamı 1, 2, 3, 5, 6 ve 7. sınıflardır; 4. sınıfta mevcut programlar devam eder. Ders bazlı istisnalar ayrıca incelenmelidir. İngilizce 2-8 programı 2025'te güncellenmiş ve 2025-2026'dan itibaren kademeli uygulamaya alınmıştır. DKAB 2026 programının 4. sınıfta uygulanması 2027-2028'e bırakılmıştır.

## Ders bazında doğrulama durumu

| Sınıf | Ders | Kaynak/sürüm | Sistemdeki durum |
|---|---|---|---|
| 4 | Sosyal Bilgiler | MEB 2018 | 7 öğrenme alanı ve 33 kazanım eklendi |
| 4 | Türkçe | MEB 2019 | Resmî PDF bulundu; aktarım bekliyor |
| 4 | Matematik | MEB 2018 | Resmî PDF bulundu; aktarım bekliyor |
| 4 | Fen Bilimleri | MEB 2018 | Resmî PDF bulundu; aktarım bekliyor |
| 4 | İngilizce | TYMM 2025 | Sınıf bazlı uygulama ve veri aktarımı takibi sürüyor |
| 4 | Din Kültürü ve Ahlak Bilgisi | TYMM 2026 | 4. sınıf 2027-2028 uygulaması; 2026-2027'de yeni program etkinleştirilmez |
| 4 | Trafik Güvenliği | TYMM 2025 | Resmî sınıf sayfası bulundu; yürürlük takvimi teyit edilecek |
| 4 | İnsan Hakları, Vatandaşlık ve Demokrasi | TTKB kataloğu | Güncel PDF ve yürürlük kontrolü bekliyor |
| 5 | Matematik | TYMM 2024 | 6 tema ve 23 öğrenme çıktısı eklendi |
| 5 | Sosyal Bilgiler | TYMM 2024 | 6 öğrenme alanı ve 19 öğrenme çıktısı eklendi |
| 5 | Fen Bilimleri | TYMM 2024 | 7 ünite ve 28 öğrenme çıktısı eklendi |
| 5 | Türkçe | TYMM 2024 | 6 tema ve tema bazlı çıktılar eklendi |
| 5 | İngilizce | TYMM 2025 | 8 tema ve 184 beceri odaklı özet eklendi |
| 5 | Din Kültürü ve Ahlak Bilgisi | TYMM 2026 | 5 ünite ve 18 öğrenme çıktısı eklendi |

## 4. sınıf Sosyal Bilgiler — MEB 2018

Resmî 2018 Sosyal Bilgiler programının 4. sınıf bölümündeki yedi öğrenme alanı ve 33 kazanım, data/curriculum/4-sosyal-bilgiler-meb-2018.json dosyasına aktarıldı. Kodlar ve kısa açıklamalar resmî PDF'den alınmıştır.

Kaynak PDF: https://mufredat.meb.gov.tr/Dosyalar/201812103847686-SOSYAL%20B%C4%B0LG%C4%B0LER%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI%20.pdf
2026-2027 TYMM kapsamı: https://tymm.meb.gov.tr/taslak-cerceve-planlari/temel-egitim

## 4. sınıfta sıradaki resmî kaynaklar

- Türkçe 2019: https://mufredat.meb.gov.tr/Dosyalar/20195716392253-02-T%C3%BCrk%C3%A7e%20%C3%96%C4%9Fretim%20Program%C4%B1%202019.pdf
- Matematik 2018: https://mufredat.meb.gov.tr/Dosyalar/201813017165445-MATEMAT%C4%B0K%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI%202018v.pdf
- Fen Bilimleri 2018: https://mufredat.meb.gov.tr/Dosyalar/201812312311937-FEN%20B%C4%B0L%C4%B0MLER%C4%B0%20%C3%96%C4%9ERET%C4%B0M%20PROGRAMI2018.pdf
- İngilizce 2025 duyurusu: https://ttkb.meb.gov.tr/www/ingilizce-dersi-ogretim-programlarinda-guncelleme-yapildi/icerik/795
- 4. sınıf İngilizce: https://tymm.meb.gov.tr/ogretim-programlari/ingilizce-dersi-temel-egitim/5
- 2026 DKAB PDF: https://mufredat.meb.gov.tr/Dosyalar/202631310725635-dkab48.pdf
- 4. sınıf Trafik Güvenliği: https://tymm.meb.gov.tr/ogretim-programlari/ders/trafik-guvenligi-dersi

## Uygulama kuralları

1. Katalogda görünmek, bir sınıfta o öğretim yılında yürürlükte olmakla aynı şey değildir.
2. Her ders için kurul kararı, uygulama yılı, sınıf kapsamı, PDF URL'si ve sürüm birlikte doğrulanır.
3. Eski JSON dosyaları tarihsel kayıt olarak korunur; yeni sürüm ayrı dosyaya aktarılır.
4. Yalnızca tema/ünite adı görülebiliyorsa kazanım kodları doğrulanmış sayılmaz.
5. Soru üretimi yalnızca ilgili sınıfta yürürlükte olan doğrulanmış kazanımlarla yapılır.

## Mevcut veri dosyaları

- data/curriculum/4-sosyal-bilgiler-meb-2018.json: 4. sınıf Sosyal Bilgiler, 7 öğrenme alanı ve 33 kazanım.
- data/curriculum/5-matematik-tymm-2024.json
- data/curriculum/5-sosyal-bilgiler-tymm-2024.json
- data/curriculum/5-fen-bilimleri-tymm-2024.json
- data/curriculum/5-turkce-tymm-2024.json
- data/curriculum/5-ingilizce-tymm-2025.json
- data/curriculum/5-dkab-tymm-2026.json

Eksik veya tahmini kazanımlarla sınav üretimi yapılmamalıdır.
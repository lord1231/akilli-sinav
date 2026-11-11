# Gemini soru üretim yönergesi

Gemini yalnızca backend üzerinden çağrılır. Modelden seçilen sınıf, ders, ünite ve MEB kazanımıyla uyumlu, özgün ve yaş düzeyine uygun çoktan seçmeli sorular istenir.

## Zorunlu çıktı kuralları
- Tam olarak 25 soru üret.
- Her soru 4 seçenekli (A, B, C, D) olsun.
- Tek bir doğru cevap bulunsun.
- Doğru cevap açıklaması kısa ve öğretici olsun.
- Kazanım dışına çıkma; bilgi uydurma.
- Çıktı JSON şemasına uysun; JSON dışında metin üretme.
- Soruları yayımlamadan önce ayrı doğrulama adımından geçir.
- Kaynak gerektiren bilgi için kaynak URL ve müfredat sürümünü kaydet.

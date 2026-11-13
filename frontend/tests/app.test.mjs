import test, { afterEach } from "node:test";
import assert from "node:assert/strict";
import { loadApp, until, tick, css, html, closeAll } from "./harness.mjs";

afterEach(closeAll);

const PARENT = { id: "p1", full_name: "Veli Test", role: "parent", email: "v@example.com" };
const STUDENT = { id: "s1", full_name: "Öğrenci Test", role: "student", email: "o@example.com", grade_level: 5 };
const subjects5 = [{ id: "sub1", grade_level: 5, name: "Türkçe", curriculum_version: "TYMM 2024" }, { id: "sub2", grade_level: 5, name: "Matematik", curriculum_version: "TYMM 2024" }];

function parentRoutes(extra = {}) {
  return {
    "GET /api/auth/me": PARENT,
    "GET /api/auth/students": [{ id: "s1", full_name: "Öğrenci Test", grade_level: 5 }],
    "GET /api/curriculum/subjects?grade=5": subjects5,
    "GET /api/curriculum/subjects/sub1/units": [{ id: "u1", name: "Ünite 1", order_no: 1 }],
    "GET /api/curriculum/units/u1/outcomes": [{ id: "o1", code: "T.5.1.1", description: "Kazanım açıklaması" }],
    "GET /api/exams": [],
    ...extra,
  };
}

test("app.js yüklenirken hata vermez (tüm HTML öğeleri mevcut)", () => {
  const app = loadApp();
  assert.deepEqual(app.errors.map(String), []);
});

test("Parolamı unuttum: form açılır ve e-posta sunucuya gönderilir", async () => {
  const app = loadApp({ routes: { "POST /api/auth/password/forgot": { message: "ok" } } });
  assert.deepEqual(app.errors.map(String), []);
  assert.equal(app.$("forgot-form").hidden, true);
  app.$("forgot-toggle").click();
  assert.equal(app.$("forgot-form").hidden, false);
  app.$("forgot-form").querySelector("input[name=email]").value = "veli@example.com";
  app.$("forgot-form").dispatchEvent(new app.window.Event("submit", { cancelable: true }));
  assert.ok(await until(() => app.calls.some((c) => c.url === "/api/auth/password/forgot")));
  assert.deepEqual(app.calls.find((c) => c.url === "/api/auth/password/forgot").body, { email: "veli@example.com" });
  assert.ok(await until(() => app.$("auth-message").textContent.includes("gönderildi")));
});

test("E-postadaki sıfırlama bağlantısı yeni parola formunu açar ve token ile gönderir", async () => {
  const token = "a".repeat(43);
  const app = loadApp({ hash: "#reset_token=" + token, routes: { "POST /api/auth/password/reset": { message: "ok" } } });
  assert.deepEqual(app.errors.map(String), []);
  assert.equal(app.$("reset-form").hidden, false);
  app.$("reset-form").querySelector("input[name=new_password]").value = "YeniGucluParola1";
  app.$("reset-form").dispatchEvent(new app.window.Event("submit", { cancelable: true }));
  assert.ok(await until(() => app.calls.some((c) => c.url === "/api/auth/password/reset")));
  assert.deepEqual(app.calls.find((c) => c.url === "/api/auth/password/reset").body, { token, new_password: "YeniGucluParola1" });
  assert.ok(await until(() => app.$("auth-message").textContent.includes("yenilendi")));
});

test("Veli paneli: dersler, üniteler ve kazanımlar listelenir", async () => {
  const app = loadApp({ token: "t", routes: parentRoutes() });
  assert.ok(await until(() => app.$("exam-outcome").options.length === 1));
  assert.deepEqual([...app.$("exam-subject").options].map((o) => o.textContent), ["Türkçe", "Matematik"]);
  assert.equal(app.$("exam-unit").options.length, 1);
  assert.equal(app.$("exam-subject-message").textContent, "");
  assert.equal(app.$("dashboard").hidden, false);
});

test("Ders listesi boşsa kullanıcıya açık mesaj gösterilir ve oturum kapanmaz", async () => {
  const app = loadApp({ token: "t", routes: parentRoutes({ "GET /api/curriculum/subjects?grade=5": [] }) });
  assert.ok(await until(() => app.$("exam-subject-message").textContent.length > 0));
  assert.match(app.$("exam-subject-message").textContent, /5\. sınıf için ders bulunamadı/);
  assert.equal(app.$("dashboard").hidden, false);
});

test("Ders API'si hata verirse oturum kapanmaz, hata gösterilir", async () => {
  const app = loadApp({ token: "t", routes: parentRoutes({ "GET /api/curriculum/subjects?grade=5": { status: 500, body: { detail: "Sunucu hatası" } } }) });
  assert.ok(await until(() => app.$("exam-subject-message").textContent.includes("Sunucu hatası")));
  assert.equal(app.$("dashboard").hidden, false);
});

test("Aynı başlıklı tamamlanmış sınavların her birinde kendi PDF düğmesi bulunur", async () => {
  const exams = [1, 2, 3].map((n) => ({ id: "e" + n, title: "Kazanım değerlendirme sınavı", status: "completed", question_count: 25, score: 40 + n }));
  const app = loadApp({ token: "t", routes: parentRoutes({ "GET /api/exams": exams }) });
  assert.ok(await until(() => app.$("exams").children.length === 3));
  for (const card of app.$("exams").children) {
    assert.equal(card.querySelectorAll("[data-result-pdf]").length, 1, "her kartta tam bir PDF düğmesi olmalı");
  }
  assert.deepEqual([...app.$("exams").querySelectorAll("[data-result-pdf]")].map((b) => b.dataset.resultPdf), ["e1", "e2", "e3"]);
});

test("Sınav durumları Türkçe etiketlerle gösterilir", async () => {
  const exams = [
    { id: "a", title: "A", status: "pending_review", question_count: 25, score: null },
    { id: "b", title: "B", status: "published", question_count: 25, score: null },
    { id: "c", title: "C", status: "rejected", question_count: 25, score: null, review_note: "Hatalı soru" },
    { id: "d", title: "D", status: "completed", question_count: 25, score: 80 },
  ];
  const app = loadApp({ token: "t", routes: parentRoutes({ "GET /api/exams": exams }) });
  assert.ok(await until(() => app.$("exams").children.length === 4));
  const text = app.$("exams").textContent;
  for (const raw of ["pending_review", "published", "rejected", "completed"]) assert.ok(!text.includes(raw), raw + " ham haliyle görünmemeli");
  for (const label of ["İncelemede", "Yayında", "Reddedildi", "Tamamlandı"]) assert.ok(text.includes(label), label);
});

const questions = Array.from({ length: 25 }, (_, i) => ({
  id: "q" + (i + 1), position: i + 1, prompt: `Soru metni ${i + 1}`,
  options: ["A", "B", "C", "D"].map((k) => ({ key: k, text: `Seçenek ${k}` })),
}));
const examBody = (over = {}) => ({
  id: "ex1", title: "Deneme", status: "published", duration_minutes: 30,
  started_at: new Date().toISOString(), deadline_at: new Date(Date.now() + 25 * 60000).toISOString(),
  server_time: new Date().toISOString(), saved_answers: {}, questions, ...over,
});
const studentRoutes = (extra = {}) => ({
  "GET /api/auth/me": STUDENT,
  "GET /api/exams?": [],
  "GET /api/exams": [{ id: "ex1", title: "Deneme", status: "published", question_count: 25, score: null }],
  "GET /api/exams/ex1": examBody(),
  "POST /api/exams/ex1/answers/": { saved: true },
  "POST /api/exams/ex1/submit": { exam_id: "ex1", correct: 20, total: 25, score: 80, status: "completed" },
  ...extra,
});

test("Öğrenci: sınav açılır, 25 soru ve 100 seçenek çizilir, cevap anında kaydedilir", async () => {
  const app = loadApp({ token: "t", routes: studentRoutes() });
  assert.ok(await until(() => app.document.querySelector("[data-open]")));
  app.document.querySelector("[data-open]").click();
  assert.ok(await until(() => app.document.querySelectorAll("#answer-form fieldset").length === 25));
  assert.equal(app.document.querySelectorAll("#answer-form input[type=radio]").length, 100);
  const radio = app.document.querySelector('input[name="q3"][value="B"]');
  radio.checked = true;
  radio.dispatchEvent(new app.window.Event("change", { bubbles: true }));
  assert.ok(await until(() => app.calls.some((c) => c.url === "/api/exams/ex1/answers/q3")));
  assert.deepEqual(app.calls.find((c) => c.url === "/api/exams/ex1/answers/q3").body, { selected_option: "B" });
  assert.ok(await until(() => app.$("save-status").textContent.includes("kaydedildi")));
});

test("Öğrenci: teslim edince sonuç (doğru/25 ve puan) gösterilir; boş soru uyarısı sorulur", async () => {
  let confirmText = "";
  const app = loadApp({ token: "t", routes: studentRoutes() });
  app.window.confirm = (t) => { confirmText = t; return true; };
  assert.ok(await until(() => app.document.querySelector("[data-open]")));
  app.document.querySelector("[data-open]").click();
  assert.ok(await until(() => app.$("answer-form")));
  app.$("answer-form").dispatchEvent(new app.window.Event("submit", { cancelable: true }));
  assert.ok(await until(() => app.$("exam-workspace").textContent.includes("Sınav tamamlandı")));
  assert.match(confirmText, /25 soru boş bırakıldı/);
  assert.match(app.$("exam-workspace").textContent, /Doğru cevap: 20\/25 • Puan: 80/);
  assert.ok(app.calls.some((c) => c.method === "POST" && c.url === "/api/exams/ex1/submit"));
});

test("Süresi dolmuş sınav açılınca otomatik teslim edilir", async () => {
  const expired = examBody({ deadline_at: new Date(Date.now() - 5000).toISOString(), server_time: new Date().toISOString() });
  const app = loadApp({ token: "t", routes: studentRoutes({ "GET /api/exams/ex1": expired }) });
  assert.ok(await until(() => app.document.querySelector("[data-open]")));
  app.document.querySelector("[data-open]").click();
  assert.ok(await until(() => app.$("exam-workspace").textContent.includes("otomatik teslim")));
});

test("Sunucu saati cihaz saatinden farklıysa kalan süre sunucuya göre hesaplanır", async () => {
  // Cihaz saati 1 saat ileri; sunucuya göre 25 dk kalmış.
  const serverNow = Date.now();
  const body = examBody({ server_time: new Date(serverNow).toISOString(), deadline_at: new Date(serverNow + 25 * 60000).toISOString() });
  const app = loadApp({ token: "t", routes: studentRoutes({ "GET /api/exams/ex1": body }) });
  const realNow = app.window.Date.now;
  app.window.Date.now = () => realNow() + 3600_000;
  assert.ok(await until(() => app.document.querySelector("[data-open]")));
  app.document.querySelector("[data-open]").click();
  assert.ok(await until(() => app.$("exam-countdown")));
  await tick(50);
  assert.match(app.$("exam-countdown").textContent, /Kalan süre: (24|25):\d\d/);
});

test("Sunucuda zaten tamamlanmış sınav açılırsa sonuç ekranı gösterilir", async () => {
  const done = examBody({ status: "completed", questions: [] });
  const app = loadApp({ token: "t", routes: studentRoutes({
    "GET /api/exams": [{ id: "ex1", title: "Deneme", status: "published", question_count: 25, score: null }],
    "GET /api/exams/ex1": done,
    "GET /api/exams/ex1/results": { score: 60, question_count: 25, details: [] },
  }) });
  assert.ok(await until(() => app.document.querySelector("[data-open]")));
  app.document.querySelector("[data-open]").click();
  assert.ok(await until(() => app.$("exam-workspace").textContent.includes("Sınav sonucu: 60/100")));
  assert.equal(app.$("answer-form"), null);
});

test("Mobil uyumluluk (statik): viewport, dar ekran kuralları ve dokunma hedefleri", () => {
  assert.match(html, /<meta name="viewport" content="width=device-width,\s*initial-scale=1/);
  assert.match(html, /<html lang="tr">/);
  assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /button\{[^}]*min-height:44px/, "mobilde düğmeler en az 44px olmalı");
  assert.match(css, /\.choice\{[^}]*min-height:48px/, "sınav seçenekleri en az 48px dokunma alanı sunmalı");
  assert.match(css, /\.choice input\{[^}]*width:22px/, "radyo düğmesi parmakla seçilebilecek boyutta olmalı");
  assert.match(css, /overflow-wrap:anywhere/, "uzun metinler taşmamalı");
});

const ADMIN = { id: "a1", full_name: "Yönetici", role: "admin", email: "admin@example.com" };
const adminRoutes = (extra = {}) => ({
  "GET /api/auth/me": ADMIN,
  "GET /api/exams/review-queue": [],
  "GET /api/admin/audit-logs": [],
  "GET /api/exams": [],
  "GET /api/curriculum/subjects/sub1/units": [{ id: "u1", name: "Ünite 1", order_no: 1 }],
  "GET /api/curriculum/units/u1/outcomes": [],
  "GET /api/curriculum/subjects": subjects5,
  ...extra,
});
const submit = (app, id) => app.$(id).dispatchEvent(new app.window.Event("submit", { cancelable: true }));
const fill = (app, formId, values) => { for (const [k, v] of Object.entries(values)) app.$(formId).querySelector(`[name=${k}]`).value = v; };

test("Yönetici: ders ekleme başarıyla biter ve ders listesi yenilenir (hata mesajı çıkmaz)", async () => {
  const app = loadApp({ token: "t", routes: adminRoutes({ "POST /api/curriculum/subjects": { id: "new" } }) });
  assert.ok(await until(() => app.$("admin-subject").options.length === 2));
  const before = app.calls.filter((c) => c.method === "GET" && c.url === "/api/curriculum/subjects").length;
  fill(app, "subject-form", { grade_level: "5", name: "Yeni Ders", curriculum_version: "TYMM 2026" });
  submit(app, "subject-form");
  assert.ok(await until(() => app.$("curriculum-message").textContent.length > 0));
  assert.match(app.$("curriculum-message").textContent, /Ders kaydedildi/);
  assert.ok(await until(() => app.calls.filter((c) => c.method === "GET" && c.url === "/api/curriculum/subjects").length > before), "liste yenilenmeli");
  assert.equal(app.$("subject-form").querySelector("[name=name]").value, "", "form temizlenmeli");
});

test("Yönetici: ünite ekleme başarıyla biter", async () => {
  const app = loadApp({ token: "t", routes: adminRoutes({ "POST /api/curriculum/units": { id: "nu" } }) });
  assert.ok(await until(() => app.$("admin-subject").options.length === 2));
  fill(app, "unit-form", { name: "Yeni Ünite", order_no: "2" });
  submit(app, "unit-form");
  assert.ok(await until(() => app.$("curriculum-message").textContent.length > 0));
  assert.equal(app.$("curriculum-message").textContent, "Ünite kaydedildi.");
});

test("Yönetici: kazanım ekleme başarıyla biter ve form temizlenir", async () => {
  const app = loadApp({ token: "t", routes: adminRoutes({ "POST /api/curriculum/outcomes": { id: "no" } }) });
  assert.ok(await until(() => app.$("admin-unit").options.length === 1));
  fill(app, "outcome-form", { code: "T.5.9.9", description: "Yeterince uzun kazanım açıklaması", source_url: "https://tymm.meb.gov.tr/x", source_version: "TYMM 2024" });
  submit(app, "outcome-form");
  assert.ok(await until(() => app.$("curriculum-message").textContent.length > 0));
  assert.equal(app.$("curriculum-message").textContent, "Kazanım kaydedildi.");
  assert.equal(app.$("outcome-form").querySelector("[name=code]").value, "");
});

test("Yönetici: toplu müfredat içe aktarma sonucu gösterilir", async () => {
  const result = { subject_id: "s", units_added: 2, outcomes_added: 7, source_url: "x", curriculum_version: "TYMM 2024" };
  const app = loadApp({ token: "t", routes: adminRoutes({ "POST /api/curriculum/import": result }) });
  assert.ok(await until(() => app.$("admin-subject").options.length === 2));
  fill(app, "curriculum-import-form", { payload: JSON.stringify({ grade_level: 5 }) });
  submit(app, "curriculum-import-form");
  assert.ok(await until(() => app.$("import-message").textContent.length > 0));
  assert.match(app.$("import-message").textContent, /Aktarım tamamlandı: 2 yeni ünite, 7 yeni kazanım/);
});

test("Yönetici: inceleme kuyruğundaki sınav onaylanınca liste yenilenir", async () => {
  let approved = false;
  const queue = () => (approved ? [] : [{ id: "ex9", title: "İncelenecek", student_id: "s1", questions: [{ id: "q1", position: 1, prompt: "Soru?", options: [], correct_option: "B", explanation: "Çünkü" }] }]);
  const app = loadApp({ token: "t", routes: adminRoutes({
    "GET /api/exams/review-queue": () => queue(),
    "POST /api/exams/ex9/approve": () => { approved = true; return { id: "ex9", status: "published", question_count: 25 }; },
  }) });
  assert.ok(await until(() => app.document.querySelector("[data-approve]")));
  app.document.querySelector("[data-approve]").click();
  assert.ok(await until(() => app.$("review-queue").textContent.includes("İnceleme bekleyen sınav yok")));
});

for (const [source, expected] of [["gemini", "25 soru üretildi."], ["pool", "25 soru onaylı soru havuzundan seçildi."]]) {
  test(`Sınav hazırlanınca kaynak (${source}) kullanıcıya doğru anlatılır`, async () => {
    const app = loadApp({ token: "t", routes: parentRoutes({ "POST /api/exams/generate": { id: "x", title: "T", question_count: 25, status: "pending_review", source } }) });
    assert.ok(await until(() => app.$("exam-outcome").options.length === 1));
    app.$("create-exam-form").dispatchEvent(new app.window.Event("submit", { cancelable: true }));
    assert.ok(await until(() => app.$("exam-message").textContent.length > 0));
    assert.ok(app.$("exam-message").textContent.startsWith(expected), app.$("exam-message").textContent);
    assert.match(app.$("exam-message").textContent, /yönetici incelemesine gönderildi/);
  });
}

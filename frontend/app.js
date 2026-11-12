let token=sessionStorage.getItem("akilli_token")||"",mode="login",role="",studentsCache=[];
const $=id=>document.getElementById(id);const val=(form,name)=>new FormData(form).get(name);
function msg(id,t){$(id).textContent=t||""}
async function api(path,options={}){const headers={"Content-Type":"application/json",...(options.headers||{})};if(token)headers.Authorization="Bearer "+token;const r=await fetch(path,{...options,headers});let d={};try{d=await r.json()}catch{}if(!r.ok)throw Error(d.detail||"İşlem başarısız.");return d}
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function setMode(v){mode=v;$("login-tab").classList.toggle("active",v==="login");$("register-tab").classList.toggle("active",v==="register");$("name-field").hidden=v==="login";$("auth-submit").textContent=v==="login"?"Giriş yap":"Veli hesabı oluştur";msg("auth-message","")}
$("login-tab").onclick=()=>setMode("login");$("register-tab").onclick=()=>setMode("register");
$("auth-form").onsubmit=async e=>{e.preventDefault();const p={email:val(e.currentTarget,"email"),password:val(e.currentTarget,"password")};try{if(mode==="register"){p.full_name=val(e.currentTarget,"full_name");await api("/api/auth/register",{method:"POST",body:JSON.stringify(p)});msg("auth-message","Kayıt tamamlandı. Şimdi giriş yapın.");setMode("login")}else{const d=await api("/api/auth/login",{method:"POST",body:JSON.stringify(p)});token=d.access_token;sessionStorage.setItem("akilli_token",token);await dashboard()}}catch(x){msg("auth-message",x.message)}};
$("logout").onclick=()=>{token="";sessionStorage.removeItem("akilli_token");$("dashboard").hidden=true;$("auth-panel").hidden=false};
$("student-form").onsubmit=async e=>{e.preventDefault();const f=e.currentTarget,p={full_name:val(f,"full_name"),email:val(f,"email"),password:val(f,"password"),grade_level:+val(f,"grade_level"),consent_confirmed:val(f,"consent_confirmed")==="on"};try{await api("/api/auth/students",{method:"POST",body:JSON.stringify(p)});msg("student-message","Öğrenci hesabı oluşturuldu.");f.reset();await loadStudents()}catch(x){msg("student-message",x.message)}};
async function loadStudents(){studentsCache=await api("/api/auth/students");$("students").innerHTML=studentsCache.map(s=>'<div class="item">'+esc(s.full_name)+' • '+s.grade_level+'. sınıf <button data-progress="'+s.id+'">Başarı raporu</button></div>').join("")||"Henüz öğrenci eklenmedi.";const select=$("exam-student");select.innerHTML=studentsCache.map(s=>'<option value="'+s.id+'">'+esc(s.full_name)+' ('+s.grade_level+'. sınıf)</option>').join("");$("create-exam-panel").hidden=studentsCache.length===0;if(studentsCache.length)await loadSubjects()}
async function loadSubjects(){const sid=$("exam-student").value;const student=studentsCache.find(s=>s.id===sid);const grade=student?.grade_level||4;const rows=await api("/api/curriculum/subjects?grade="+grade);$("exam-subject").innerHTML=rows.map(x=>'<option value="'+x.id+'">'+esc(x.name)+'</option>').join("");$("admin-subject").innerHTML=rows.map(x=>'<option value="'+x.id+'">'+x.grade_level+'. sınıf • '+esc(x.name)+'</option>').join("");if(rows.length)await loadUnits(rows[0].id);else{$("exam-unit").innerHTML="";$("exam-outcome").innerHTML=""}}
async function loadUnits(subjectId){const rows=await api("/api/curriculum/subjects/"+subjectId+"/units");$("exam-unit").innerHTML=rows.map(x=>'<option value="'+x.id+'">'+esc(x.name)+'</option>').join("");$("admin-unit").innerHTML=rows.map(x=>'<option value="'+x.id+'">'+esc(x.name)+'</option>').join("");if(rows.length)await loadOutcomes(rows[0].id);else $("exam-outcome").innerHTML=""}
async function loadOutcomes(unitId){const rows=await api("/api/curriculum/units/"+unitId+"/outcomes");$("exam-outcome").innerHTML=rows.map(x=>'<option value="'+x.id+'">'+esc(x.code)+' • '+esc(x.description)+'</option>').join("")}
$("exam-student").onchange=loadSubjects;$("exam-subject").onchange=e=>loadUnits(e.target.value);$("exam-unit").onchange=e=>loadOutcomes(e.target.value);
$("create-exam-form").onsubmit=async e=>{e.preventDefault();try{const d=await api("/api/exams/generate",{method:"POST",body:JSON.stringify({student_id:val(e.currentTarget,"student_id"),learning_outcome_id:val(e.currentTarget,"learning_outcome_id"),title:val(e.currentTarget,"title")})});msg("exam-message","25 soru üretildi. Güvenlik ve kalite için yönetici incelemesine gönderildi.");await loadExams()}catch(x){msg("exam-message",x.message)}};
async function loadExams(){const a=await api("/api/exams");$("exams").innerHTML=a.map(x=>'<div class="item"><strong>'+esc(x.title)+'</strong><p>'+x.question_count+' soru • '+esc(x.status)+(x.score==null?"":" • Puan: "+x.score)+'</p>'+(x.review_note?'<p>Yönetici notu: '+esc(x.review_note)+'</p>': '')+(role==="student"&&x.status==="published"?'<button data-open="'+x.id+'">Sınava gir</button>':x.status==="completed"?'<button data-result="'+x.id+'">Sonucu gör</button>':"")+'</div>').join("")||"Henüz sınav bulunmuyor."}
$("exams").addEventListener("click",async e=>{try{const open=e.target.closest("[data-open]"),result=e.target.closest("[data-result]");if(open)await openExam(open.dataset.open);if(result)await showResult(result.dataset.result)}catch(x){msg("exam-workspace",x.message);$("exam-workspace").hidden=false}});
let examClock=null;
async function openExam(id){
 if(examClock){clearInterval(examClock);examClock=null}
 const data=await api("/api/exams/"+id);
 let html='<h2>'+esc(data.title)+'</h2><div class="exam-status"><strong id="exam-countdown">Süre hesaplanıyor…</strong><span id="save-status">Cevaplar otomatik kaydedilir.</span></div><p>Her seçimin sunucuya kaydedilir. İnternet kesilirse bağlantı geldiğinde tekrar deneyebilirsin.</p><form id="answer-form">';
 for(const q of data.questions){
  html+='<fieldset class="item"><legend>'+q.position+'. '+esc(q.prompt)+'</legend>';
  for(const o of q.options){const checked=data.saved_answers?.[q.id]===o.key?' checked':'';html+='<label class="check"><input type="radio" name="'+q.id+'" value="'+o.key+'"'+checked+'> '+o.key+') '+esc(o.text)+'</label>'}
  html+='</fieldset>';
 }
 html+='<button class="primary" id="submit-exam">Sınavı teslim et</button></form>';
 $("exam-workspace").innerHTML=html;$("exam-workspace").hidden=false;
 const form=$("answer-form"),pending=new Set(),failed=new Map();let submitted=false;
 async function saveChoice(questionId,choice){
  pending.add(questionId);$("save-status").textContent="Kaydediliyor…";
  try{await api("/api/exams/"+id+"/answers/"+questionId,{method:"POST",body:JSON.stringify({selected_option:choice})});failed.delete(questionId);sessionStorage.removeItem("exam-pending-"+id+"-"+questionId)}
  catch(err){failed.set(questionId,choice);sessionStorage.setItem("exam-pending-"+id+"-"+questionId,choice);$("save-status").textContent="Bağlantı bekleniyor; cevap cihazda geçici olarak saklandı."}
  finally{pending.delete(questionId);if(!pending.size&&!failed.size)$("save-status").textContent="Tüm cevaplar kaydedildi."}
 }
 form.addEventListener("change",ev=>{const input=ev.target;if(input.matches('input[type="radio"]'))saveChoice(input.name,input.value)});
 async function retryFailed(){
  for(const [qid,choice] of [...failed.entries()])await saveChoice(qid,choice);
 }
 window.addEventListener("online",retryFailed);
 function remainingSeconds(){
  if(!data.deadline_at)return 30*60;
  return Math.max(0,Math.floor((new Date(data.deadline_at).getTime()-Date.now())/1000));
 }
 async function tick(){
  const left=remainingSeconds(),mins=Math.floor(left/60),secs=left%60;
  $("exam-countdown").textContent="Kalan süre: "+String(mins).padStart(2,"0")+":"+String(secs).padStart(2,"0");
  if(left<=0&&!submitted){submitted=true;clearInterval(examClock);examClock=null;await retryFailed();await finishExam(true)}
 }
 async function finishExam(auto){
  if(pending.size)await new Promise(resolve=>{const wait=()=>pending.size?setTimeout(wait,150):resolve();wait()});
  if(failed.size){$("save-status").textContent="Bazı cevaplar henüz sunucuya ulaşmadı. Bağlantı kurulunca tekrar deneyin.";submitted=false;return}
  try{
   const score=await api("/api/exams/"+id+"/submit",{method:"POST"});
   if(examClock){clearInterval(examClock);examClock=null}
   window.removeEventListener("online",retryFailed);
   $("exam-workspace").innerHTML='<h2>Sınav tamamlandı</h2><p>Doğru cevap: '+score.correct+'/25 • Puan: '+score.score+'</p>'+(auto?'<p>Süre dolduğu için sınav otomatik teslim edildi.</p>':'');
   await loadExams();
  }catch(err){$("save-status").textContent=err.message;submitted=false}
 }
 form.onsubmit=async ev=>{
  ev.preventDefault();
  const unanswered=data.questions.filter(q=>!form.querySelector('input[name="'+q.id+'"]:checked')).length;
  const confirmation=unanswered?unanswered+" soru boş bırakıldı ve yanlış sayılacak. Cevaplarını yine de teslim etmek istiyor musun?":"Cevaplarını teslim etmek istiyor musun?";
  if(!confirm(confirmation))return;
  submitted=true;await retryFailed();await finishExam(false);
 };
 await tick();
 examClock=setInterval(tick,1000);
}
async function showResult(id){const d=await api("/api/exams/"+id+"/results");let html='<h2>Sınav sonucu: '+d.score+'/100</h2>';for(const q of d.details){html+='<div class="item"><strong>'+q.position+'. '+esc(q.prompt)+'</strong><p>Senin cevabın: '+(q.selected_option||"Boş")+' • Doğru cevap: '+q.correct_option+'</p><p>'+esc(q.explanation)+'</p></div>'}$("exam-workspace").innerHTML=html;$("exam-workspace").hidden=false}
async function loadReview(){const a=await api("/api/exams/review-queue");$("review-queue").innerHTML=a.map(x=>'<div class="item"><strong>'+esc(x.title)+'</strong><p>'+x.questions.length+' soru</p>'+x.questions.map(q=>'<p>'+q.position+'. '+esc(q.prompt)+'<br>Doğru cevap: '+q.correct_option+' • '+esc(q.explanation)+'</p>').join("")+'<button data-approve="'+x.id+'">İncele ve yayımla</button> <button data-reject="'+x.id+'">Gerekçeyle reddet</button></div>').join("")||"İnceleme bekleyen sınav yok."}
$("review-queue").addEventListener("click",async e=>{const approve=e.target.closest("[data-approve]"),reject=e.target.closest("[data-reject]");if(!approve&&!reject)return;try{if(approve){if(!confirm("Bu 25 soruyu kontrol ettiğini ve öğrenciye yayımlamayı onaylıyor musun?"))return;await api("/api/exams/"+approve.dataset.approve+"/approve",{method:"POST"})}else{const reason=prompt("Reddetme gerekçesini yaz (en az 5 karakter):");if(reason===null)return;if(reason.trim().length<5){alert("Lütfen en az 5 karakterlik bir gerekçe yaz.");return}await api("/api/exams/"+reject.dataset.reject+"/reject",{method:"POST",body:JSON.stringify({reason})})}await loadReview();await loadExams()}catch(x){$("review-queue").textContent=x.message}});
async function refreshAdminSubjects(selectedId=null){const subjects=await api("/api/curriculum/subjects");$("admin-subject").innerHTML=subjects.map(x=>'<option value="'+x.id+'">'+x.grade_level+'. sınıf • '+esc(x.name)+' • '+esc(x.curriculum_version)+'</option>').join("");if(selectedId&&subjects.some(x=>x.id===selectedId))$("admin-subject").value=selectedId;if($("admin-subject").value)await loadAdminUnits($("admin-subject").value);else $("admin-unit").innerHTML=""}
$("subject-form").onsubmit=async e=>{e.preventDefault();try{await api("/api/curriculum/subjects",{method:"POST",body:JSON.stringify({grade_level:+val(e.currentTarget,"grade_level"),name:val(e.currentTarget,"name"),curriculum_version:val(e.currentTarget,"curriculum_version")})});msg("curriculum-message","Ders kaydedildi. Ders listesi yenilendi.");e.currentTarget.reset();await refreshAdminSubjects()}catch(x){msg("curriculum-message",x.message)}};
$("unit-form").onsubmit=async e=>{e.preventDefault();try{await api("/api/curriculum/units",{method:"POST",body:JSON.stringify({subject_id:val(e.currentTarget,"subject_id"),name:val(e.currentTarget,"name"),order_no:+val(e.currentTarget,"order_no")})});msg("curriculum-message","Ünite kaydedildi.");await loadUnits(val(e.currentTarget,"subject_id"))}catch(x){msg("curriculum-message",x.message)}};
$("outcome-form").onsubmit=async e=>{e.preventDefault();try{await api("/api/curriculum/outcomes",{method:"POST",body:JSON.stringify({unit_id:val(e.currentTarget,"unit_id"),code:val(e.currentTarget,"code"),description:val(e.currentTarget,"description"),source_url:val(e.currentTarget,"source_url")||null,source_version:val(e.currentTarget,"source_version")||null})});msg("curriculum-message","Kazanım kaydedildi.");e.currentTarget.reset()}catch(x){msg("curriculum-message",x.message)}};
async function dashboard(){try{const u=await api("/api/auth/me");role=u.role;$("auth-panel").hidden=true;$("dashboard").hidden=false;$("welcome").textContent=u.full_name+" • "+u.role;$("parent-tools").hidden=role!=="parent";$("student-tools").hidden=role!=="student";$("admin-tools").hidden=role!=="admin";if(role==="parent"){await loadStudents()}if(role==="admin"){await loadReview();const s=await api("/api/curriculum/subjects");$("admin-subject").innerHTML=s.map(x=>'<option value="'+x.id+'">'+x.grade_level+'. sınıf • '+esc(x.name)+'</option>').join("")}await loadExams()}catch(x){token="";sessionStorage.removeItem("akilli_token");$("dashboard").hidden=true;$("auth-panel").hidden=false;msg("auth-message",x.message)}}
if(token)dashboard();

async function loadAdminUnits(subjectId){const a=await api("/api/curriculum/subjects/"+subjectId+"/units");$("admin-unit").innerHTML=a.map(x=>'<option value="'+x.id+'">'+esc(x.name)+'</option>').join("")}
$("admin-subject").onchange=e=>loadAdminUnits(e.target.value).catch(x=>msg("curriculum-message",x.message));
if(role==="admin"&&$("admin-subject").value)loadAdminUnits($("admin-subject").value).catch(x=>msg("curriculum-message",x.message));

$("students").addEventListener("click",async e=>{const b=e.target.closest("[data-progress]");if(!b)return;try{const d=await api("/api/auth/students/"+b.dataset.progress+"/progress");let html='<h2>Öğrenci başarı raporu</h2><p>Tamamlanan sınav: '+d.completed_exam_count+' • Ortalama puan: '+(d.average_score??"Henüz yok")+'</p><h3>Son sınavlar</h3>';html+=d.recent_exams.map(x=>'<div class="item">'+esc(x.title)+' • '+x.score+'/100</div>').join("")||"Henüz sınav yok.";html+='<h3>Geliştirilmesi gereken kazanımlar</h3>';html+=d.learning_outcomes.map(x=>'<div class="item">'+esc(x.code)+' • '+esc(x.description)+'<p>Başarı: %'+x.success_rate+' ('+x.correct+'/'+x.answered+')</p></div>').join("")||"Henüz kazanım verisi yok."; $("exam-workspace").innerHTML=html;$("exam-workspace").hidden=false}catch(x){msg("exam-workspace",x.message);$("exam-workspace").hidden=false}});

$("curriculum-import-form").onsubmit=async e=>{e.preventDefault();try{const payload=JSON.parse(val(e.currentTarget,"payload"));const result=await api("/api/curriculum/import",{method:"POST",body:JSON.stringify(payload)});msg("import-message","Aktarım tamamlandı: "+result.units_added+" yeni ünite, "+result.outcomes_added+" yeni kazanım. Sürüm: "+result.curriculum_version);e.currentTarget.reset();if(role==="admin"){const subjects=await api("/api/curriculum/subjects");$("admin-subject").innerHTML=subjects.map(x=>'<option value="'+x.id+'">'+x.grade_level+'. sınıf • '+esc(x.name)+' • '+esc(x.curriculum_version)+'</option>').join("")}}catch(x){msg("import-message",x.message)}};


$("forgot-toggle").onclick=()=>{$("forgot-form").hidden=!$("forgot-form").hidden;$("reset-form").hidden=true};
$("forgot-form").onsubmit=async e=>{e.preventDefault();try{const email=val(e.currentTarget,"email");await api("/api/auth/password/forgot",{method:"POST",body:JSON.stringify({email})});msg("auth-message","E-posta adresi kayıtlıysa parola yenileme bağlantısı gönderildi.");e.currentTarget.reset()}catch(x){msg("auth-message",x.message)}};
const resetToken=new URLSearchParams(window.location.search).get("reset_token");
if(resetToken){$("auth-panel").hidden=false;$("reset-form").hidden=false;$("forgot-form").hidden=true;$("forgot-toggle").hidden=true;msg("auth-message","Yeni parolanızı belirleyin.");}
$("reset-form").onsubmit=async e=>{e.preventDefault();try{await api("/api/auth/password/reset",{method:"POST",body:JSON.stringify({token:resetToken,new_password:val(e.currentTarget,"new_password")})});history.replaceState(null,"",window.location.pathname);$("reset-form").hidden=true;$("forgot-toggle").hidden=false;msg("auth-message","Parolanız yenilendi. Yeni parolanızla giriş yapabilirsiniz.");e.currentTarget.reset()}catch(x){msg("auth-message",x.message)}};

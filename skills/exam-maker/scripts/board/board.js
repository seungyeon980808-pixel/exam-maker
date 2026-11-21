// 코멘트판: 칸에 적으면 0.6초 뒤 자동 저장(코멘트 서버 → 시안 폴더의 comments_<판>.json).
// 서버 없이 파일로 열었을 때는 이 브라우저(localStorage)에만 남기고, 「코멘트 전체 복사」로 Claude에게 붙여 넣는다.
const st = document.getElementById('st');
const ver = encodeURIComponent(document.body.dataset.version || 'v');
const LS = 'exam-comments-' + document.body.dataset.key;
const boxes = [...document.querySelectorAll('textarea[data-q]')];
let timer = null, data = {}, server = location.protocol.startsWith('http');
function show(msg, cls) { st.textContent = msg; st.className = cls || ''; }
async function load() {
  try {
    if (!server) throw 0;
    const r = await fetch('/api/comments?v=' + ver, { cache: 'no-store' });
    if (!r.ok) throw 0;
    data = await r.json(); show('불러옴 · 적으면 자동 저장', 'ok');
  } catch {
    server = false;
    try { data = JSON.parse(localStorage.getItem(LS) || '{}'); } catch { data = {}; }
    show('서버 없이 열림 · 이 브라우저에만 저장 · 끝나면 「코멘트 전체 복사」', 'bad');
  }
  for (const t of boxes) { const v = (data[t.dataset.q] || {})[t.dataset.part]; if (v) t.value = v; }
}
async function save() {
  for (const t of boxes) { (data[t.dataset.q] ||= {})[t.dataset.part] = t.value; }
  try { localStorage.setItem(LS, JSON.stringify(data)); } catch {}
  if (!server) { show('이 브라우저에 저장됨 ' + new Date().toLocaleTimeString('ko-KR'), 'bad'); return; }
  try {
    const r = await fetch('/api/comments?v=' + ver, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) });
    if (!r.ok) throw 0;
    show('저장됨 ' + new Date().toLocaleTimeString('ko-KR'), 'ok');
  } catch { show('저장 실패 · 이 브라우저에만 남음', 'bad'); }
}
boxes.forEach(t => t.addEventListener('input', () => { show('저장 중…'); clearTimeout(timer); timer = setTimeout(save, 600); }));
document.getElementById('copy').addEventListener('click', async () => {
  const lines = [];
  for (const t of boxes) if (t.value.trim()) lines.push(`${t.dataset.q}번 [${t.dataset.part}] ${t.value.trim()}`);
  const text = lines.length ? `코멘트판(${decodeURIComponent(ver)}) 코멘트입니다. 반영해 주세요.\n` + lines.join('\n') : '(코멘트 없음)';
  try { await navigator.clipboard.writeText(text); show(`코멘트 ${lines.length}개 복사됨`, 'ok'); }
  catch { prompt('아래 내용을 복사하세요', text); }
});
// 비교 시안: 바뀐 판에서 이전 판에 없던 문장·칸·선지를 노랗게 칠한다.
for (const sec of document.querySelectorAll('section.cmp')) {
  const [oldP, newP] = sec.querySelectorAll('.paper');
  const sel = 'p, td, th, .choices > span, .eq, .cap';
  const olds = new Set([...oldP.querySelectorAll(sel)].map(e => e.textContent.trim()));
  for (const e of newP.querySelectorAll(sel)) if (e.textContent.trim() && !olds.has(e.textContent.trim())) e.style.background = '#fff1a8';
}
load();

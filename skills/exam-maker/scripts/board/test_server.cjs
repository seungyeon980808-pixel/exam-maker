// 코멘트 서버 자체 검사: 띄워서 쪽 열기·저장·읽기·폴더 밖 막기를 확인하고 끈다.
// 실행: node test_server.cjs <시안폴더>
const { spawn } = require('node:child_process');
const path = require('node:path');
const dir = path.resolve(process.argv[2] || '.');
const port = 8000 + Math.floor(Math.random() * 900);
const s = spawn(process.execPath, [path.join(__dirname, 'comment_server.cjs'), dir, String(port)], { stdio: 'inherit' });
const b = `http://127.0.0.1:${port}`;
const fail = (m) => { console.error('❌ ' + m); s.kill(); process.exit(1); };
setTimeout(async () => {
  try {
    let r = await fetch(b + '/'); if (r.status !== 200) fail('쪽 열기 ' + r.status);
    r = await fetch(b + '/api/comments?v=test', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ 1: { 전체: '시험' } }) });
    if (r.status !== 200) fail('저장 ' + r.status);
    r = await fetch(b + '/api/comments?v=test'); const j = await r.json(); if (j['1']['전체'] !== '시험') fail('읽기');
    r = await fetch(b + '/..%2F..%2Fpackage.json'); if (r.status !== 404) fail('폴더 밖이 열림');
    console.log('✅ 코멘트 서버 정상');
    s.kill(); process.exit(0);
  } catch (e) { fail(String(e)); }
}, 800);

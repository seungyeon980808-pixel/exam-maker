// 코멘트판 서버: 시안 폴더를 보여 주고, 코멘트를 그 폴더의 comments_<판>.json에 저장한다.
// 이 컴퓨터 안에서만(127.0.0.1) 열린다. 바깥으로 아무것도 보내지 않는다.
// 실행: node comment_server.cjs <시안폴더> [포트=8883]   → 브라우저로 http://127.0.0.1:8883 열기
const http = require('node:http'), fs = require('node:fs'), path = require('node:path');
const ROOT = path.resolve(process.argv[2] || '.');
const PORT = Number(process.argv[3] || process.env.PORT || 8883);
const TYPES = { '.html': 'text/html; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.pdf': 'application/pdf' };
const cfile = (v) => path.join(ROOT, 'comments_' + String(v || 'v').replace(/[^\w.\-]/g, '_') + '.json');

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname === '/api/comments') {
    const CF = cfile(url.searchParams.get('v'));
    if (req.method === 'GET') {
      res.writeHead(200, { 'content-type': TYPES['.json'], 'cache-control': 'no-store' });
      return res.end(fs.existsSync(CF) ? fs.readFileSync(CF) : '{}');
    }
    if (req.method === 'POST') {
      let body = '';
      req.on('data', (c) => { body += c; if (body.length > 4e6) req.destroy(); });
      return req.on('end', () => {
        try {
          const d = JSON.parse(body);
          if (fs.existsSync(CF)) fs.copyFileSync(CF, CF.replace(/\.json$/, '.bak.json'));
          fs.writeFileSync(CF, JSON.stringify(d, null, 1));
          res.writeHead(200); res.end('{}');
        } catch { res.writeHead(400); res.end('bad'); }
      });
    }
  }
  let rel = decodeURIComponent(url.pathname);
  if (rel === '/') rel = '/index.html';
  const p = path.normalize(path.join(ROOT, rel));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' }); return res.end('없음'); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(p).toLowerCase()] || 'application/octet-stream', 'cache-control': 'no-store' });
  fs.createReadStream(p).pipe(res);
}).listen(PORT, '127.0.0.1', () => console.log(`코멘트판: http://127.0.0.1:${PORT}  (폴더 ${ROOT})`));

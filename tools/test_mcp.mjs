// 교육과정 MCP 실행기 자체 검사: 띄워서 initialize → 성취기준 검색을 해 보고 끈다(최대 180초).
// 실행: node tools/test_mcp.mjs
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const p = spawn(process.execPath, [join(here, 'curriculum-mcp.mjs')], { stdio: ['pipe', 'pipe', 'inherit'] });
let buf = '';
const done = (ok, msg) => { console.log((ok ? '✅ ' : '❌ ') + msg); p.kill(); process.exit(ok ? 0 : 1); };
const timer = setTimeout(() => done(false, '180초 안에 답이 없음'), 180000);
p.stdout.on('data', (d) => {
  buf += d;
  for (const line of buf.split('\n')) {
    if (!line.includes('"id":2')) continue;
    const r = JSON.parse(line);
    const total = JSON.parse(r.result.content[0].text).total;
    clearTimeout(timer);
    done(total > 0, `교육과정 MCP 정상 (「세포」 성취기준 ${total}개)`);
  }
});
const send = (o) => p.stdin.write(JSON.stringify(o) + '\n');
send({ jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'test', version: '1' } } });
send({ jsonrpc: '2.0', method: 'notifications/initialized' });
send({ jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'search_standards', arguments: { query: '세포' } } });

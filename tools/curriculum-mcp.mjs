#!/usr/bin/env node
// 교육과정 MCP(2022 개정 중·고 성취기준 3,838개, 원문 포함) 실행기.
// 패키지: korean-secondary-learning-map-mcp (npm 공개, MIT) — https://github.com/raphysicst-create/korean-secondary-learning-map-mcp
// 처음 한 번 ~/.exam-maker/curriculum-mcp 에 설치하고, 그다음부터는 바로 띄운다. 외부 통신 없이 내장 자료만 읽는다.
// stdout은 MCP 통신 전용이라 설치 안내는 모두 stderr로 보낸다.
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const VERSION = '0.3.0';
const PKG = 'korean-secondary-learning-map-mcp';
const dir = join(process.env.EXAM_MAKER_HOME || join(homedir(), '.exam-maker'), 'curriculum-mcp');
const cli = join(dir, 'node_modules', PKG, 'src', 'cli.mjs');

if (!existsSync(cli)) {
  mkdirSync(dir, { recursive: true });
  console.error(`[exam-maker] 교육과정 MCP ${VERSION} 처음 설치 중… (${dir})`);
  const r = spawnSync('npm', ['install', '--no-audit', '--no-fund', '--prefix', dir, `${PKG}@${VERSION}`], {
    stdio: ['ignore', process.stderr, process.stderr],
    shell: process.platform === 'win32',
  });
  if (r.status !== 0 || !existsSync(cli)) {
    console.error('[exam-maker] 교육과정 MCP 설치 실패. Node.js(npm)가 설치되어 있는지, 인터넷이 되는지 확인하세요.');
    process.exit(1);
  }
}
await import(pathToFileURL(cli).href);

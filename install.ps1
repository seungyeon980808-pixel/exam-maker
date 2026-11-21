# exam-maker 한 번에 설치 (윈도우 PowerShell)
# 실행: irm https://raw.githubusercontent.com/seungyeon980808-pixel/exam-maker/main/install.ps1 | iex
#   또는 저장소를 받은 뒤: pwsh -File install.ps1 [-SkipLogin]   (이 파일은 BOM 없는 UTF-8이라 irm|iex·PowerShell 7에 맞춤)
# 하는 일: Node·Python·Typst·Git 설치(없을 때만) → 파이썬 도구 → Codex·Claude 명령줄 → exam-maker·5e-figure 플러그인 → codex login → 설치 확인
# 이미 있는 것은 건너뛰므로 여러 번 실행해도 된다. 시험 파일은 아무것도 내려받거나 올리지 않는다.
param([switch]$SkipLogin)

$ErrorActionPreference = 'Continue'
if ($env:EXAM_MAKER_SKIP_LOGIN) { $SkipLogin = $true }
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$env:PYTHONUTF8 = '1'
$fail = @()

function Step($t) { Write-Host ""; Write-Host "▶ $t" -ForegroundColor Cyan }
function Ok($t) { Write-Host "  ✔ $t" -ForegroundColor Green }
function Warn($t) { Write-Host "  ! $t" -ForegroundColor Yellow }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
  $npmBin = Join-Path $env:APPDATA 'npm'
  if ((Test-Path $npmBin) -and ($env:Path -notlike "*$npmBin*")) { $env:Path += ";$npmBin" }
}
function Works($cmd, $arg) {
  # 윈도우 스토어의 가짜 python(설치 안내 창만 띄움)을 걸러 내려고 실제로 실행해 본다.
  try { $null = & $cmd $arg 2>$null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}
function Winget-Install($id, $name) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Warn "winget이 없어 $name 을(를) 설치하지 못했습니다. 직접 설치해 주세요."; $script:fail += $name; return }
  Write-Host "  $name 설치 중… (관리자 확인 창이 뜨면 「예」)"
  winget install --id $id -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
  Refresh-Path
}

Refresh-Path
Step "1/6 프로그램 (Node.js · Python · Typst · Git)"
if (Works 'node' '--version') { Ok "Node.js $(node --version)" } else { Winget-Install 'OpenJS.NodeJS.LTS' 'Node.js' }
if (Works 'python' '--version') { Ok "$(python --version)" } else { Winget-Install 'Python.Python.3.12' 'Python' }
if (Works 'typst' '--version') { Ok "$(typst --version)" } else { Winget-Install 'Typst.Typst' 'Typst' }
if (Works 'git' '--version') { Ok "$(git --version)" } else { Winget-Install 'Git.Git' 'Git' }
Refresh-Path
foreach ($c in @('node', 'python', 'typst', 'git')) { if (-not (Works $c '--version')) { Warn "$c 를 아직 찾지 못했습니다(설치 직후면 PowerShell을 다시 열고 이 스크립트를 한 번 더 실행)."; $fail += $c } }

Step "2/6 파이썬 도구 (PDF·그림·한글 자동화)"
python -m pip install --user --upgrade --quiet pymupdf pillow pyhwpx pywin32 2>&1 | Out-Host
if ($LASTEXITCODE -eq 0) { Ok "pymupdf · pillow · pyhwpx · pywin32" } else { Warn "파이썬 도구 설치 실패"; $fail += 'pip' }

Step "3/6 Codex(GPT) · Claude 명령줄"
if (-not (Works 'codex' '--version')) { npm install -g @openai/codex 2>&1 | Out-Host; Refresh-Path }
if (Works 'codex' '--version') { Ok "codex $(codex --version)" } else { Warn "codex 설치 실패"; $fail += 'codex' }
if (-not (Works 'claude' '--version')) { npm install -g @anthropic-ai/claude-code 2>&1 | Out-Host; Refresh-Path }
if (Works 'claude' '--version') { Ok "claude $(claude --version)" } else { Warn "claude 명령줄 설치 실패"; $fail += 'claude' }

Step "4/6 exam-maker · 5e-figure(그림 엔진) 플러그인"
$list = (claude plugin marketplace list 2>&1) -join "`n"
if ($list -match 'exam-maker') { claude plugin marketplace update exam-maker 2>&1 | Out-Host }
else { claude plugin marketplace add seungyeon980808-pixel/exam-maker 2>&1 | Out-Host }
$plugins = (claude plugin list 2>&1) -join "`n"
if ($plugins -match 'exam-maker@exam-maker') { claude plugin update exam-maker@exam-maker 2>&1 | Out-Host }
else { claude plugin install exam-maker@exam-maker 2>&1 | Out-Host }
$plugins = (claude plugin list 2>&1) -join "`n"
if ($plugins -match 'exam-maker@exam-maker') { Ok "exam-maker 설치됨" } else { Warn "플러그인 설치 실패"; $fail += 'plugin' }
# 그림 엔진(5e-figure)도 같이 설치
$list = (claude plugin marketplace list 2>&1) -join "`n"
if ($list -match '5e-figure') { claude plugin marketplace update 5e-figure 2>&1 | Out-Host }
else { claude plugin marketplace add seungyeon980808-pixel/5e-figure 2>&1 | Out-Host }
$plugins = (claude plugin list 2>&1) -join "`n"
if ($plugins -match '5e-figure@5e-figure') { claude plugin update 5e-figure@5e-figure 2>&1 | Out-Host }
else { claude plugin install 5e-figure@5e-figure 2>&1 | Out-Host }
$plugins = (claude plugin list 2>&1) -join "`n"
if ($plugins -match '5e-figure@5e-figure') { Ok "5e-figure(그림 엔진) 설치됨" } else { Warn "그림 엔진 설치 실패(그림은 GPT 대체 도구로 만듭니다)" }

Step "5/6 교육과정 MCP 미리 받기"
$root = Join-Path $HOME '.claude\plugins\marketplaces\exam-maker'
if (Test-Path (Join-Path $root 'tools\test_mcp.mjs')) {
  node (Join-Path $root 'tools\test_mcp.mjs') 2>$null | Out-Host
  if ($LASTEXITCODE -eq 0) { Ok "교육과정 MCP 준비됨" } else { Warn "교육과정 MCP 준비 실패(Claude 앱이 처음 연결할 때 다시 시도합니다)" }
}

Step "6/6 ChatGPT(Codex) 로그인"
$auth = Join-Path $HOME '.codex\auth.json'
if (Test-Path $auth) { Ok "이미 로그인됨" }
elseif ($SkipLogin) { Warn "로그인 건너뜀(-SkipLogin). 나중에 PowerShell에서 codex login" }
else { Write-Host "  브라우저가 열리면 ChatGPT 계정으로 로그인하세요."; codex login | Out-Host }

Step "설치 확인"
$doctor = Join-Path $root 'skills\exam-maker\scripts\doctor.py'
if (Test-Path $doctor) { python $doctor | Out-Host }

Write-Host ""
if ($fail.Count -eq 0) {
  Write-Host "끝났습니다. Claude 앱을 완전히 껐다 켠 뒤 Code 탭에서 「기말고사 출제를 시작하자」라고 말하세요." -ForegroundColor Green
} else {
  Write-Host ("다 되지 않은 것: " + ($fail -join ', ') + " — PowerShell을 다시 열고 이 설치를 한 번 더 실행해 보세요.") -ForegroundColor Yellow
}

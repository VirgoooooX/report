param(
  [ValidateSet("patch", "minor", "major")]
  [string]$Level = "patch",
  [string]$Remote = "origin",
  [string]$Branch = "",
  [string]$Message = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Resolve-Path "$ScriptDir\.."

# 1. 确保在 Git 仓库内
Push-Location $RootDir
try {
  git rev-parse --is-inside-work-tree 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Error "Not inside a Git worktree."
    exit 1
  }
} finally { Pop-Location }

# 2. 后端测试
Write-Host "=== Running backend tests ===" -ForegroundColor Cyan
Push-Location $RootDir
$env:PYTHONPATH = "backend"
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { Write-Error "Backend tests failed"; exit 1 }
Pop-Location

# 3. 前端测试
Write-Host "=== Running frontend tests ===" -ForegroundColor Cyan
Push-Location $RootDir
npm --prefix frontend test
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend tests failed"; exit 1 }
Pop-Location

# 4. 前端构建检查
Write-Host "=== Running frontend build check ===" -ForegroundColor Cyan
Push-Location $RootDir
npm --prefix frontend run build:check
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build check failed"; exit 1 }
Pop-Location

# 5. Docker 构建（如可用）
Push-Location $RootDir
$dockerAvailable = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerAvailable) {
  Write-Host "=== Running Docker build ===" -ForegroundColor Cyan
  docker compose build
  if ($LASTEXITCODE -ne 0) { Write-Warning "Docker build failed (non-blocking)" }
} else {
  Write-Host "Docker not available, skipping" -ForegroundColor Yellow
}
Pop-Location

# 6. 版本号提升
Write-Host "=== Bumping version ===" -ForegroundColor Cyan
Push-Location $RootDir
$newVersion = node scripts/bump-version.mjs $Level
if ($LASTEXITCODE -ne 0) { Write-Error "Version bump failed"; exit 1 }
Pop-Location

# 7. 暂存文件
Push-Location $RootDir
git add -A
Pop-Location

# 8. 提交
$commitMsg = if ($Message) { $Message } else { "chore: release v$newVersion" }
Push-Location $RootDir
git commit -m $commitMsg
Pop-Location

# 9. 标签
Push-Location $RootDir
git tag "v$newVersion"
Pop-Location

# 10. 推送分支
$branch = if ($Branch) { $Branch } else { git branch --show-current }
Push-Location $RootDir
git push $Remote "$branch"
Pop-Location

# 11. 推送标签
Push-Location $RootDir
git push $Remote "v$newVersion"
Pop-Location

# 12. 打印 Actions URL
Write-Host ""
Write-Host "=== Push complete ===" -ForegroundColor Green
Write-Host "Version: v$newVersion" -ForegroundColor Green
Write-Host "Actions: https://github.com/VirgoooooX/report/actions" -ForegroundColor Cyan

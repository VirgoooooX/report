param(
  [ValidateSet("patch", "minor", "major")]
  [string]$Level = "patch",
  [string]$Version = "",
  [string]$Remote = "origin",
  [string]$Branch = "",
  [string]$Message = ""
)

$ErrorActionPreference = "Stop"

# 互斥校验：-Version 与 -Level 不能同时显式指定
if ($Version -and $PSBoundParameters.ContainsKey('Level')) {
  Write-Error "-Version and -Level are mutually exclusive."
  exit 1
}

# semver 格式校验（与 bump-version.mjs 保持一致）
if ($Version -and $Version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$') {
  Write-Error "Invalid -Version: $Version (expect x.y.z[-prerelease][+build])"
  exit 1
}
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

# 5. Docker 构建检查
Push-Location $RootDir
$dockerAvailable = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerAvailable) {
  Write-Host "=== Running Docker build check ===" -ForegroundColor Cyan
  $buildxAvailable = docker buildx version 2>$null
  if ($LASTEXITCODE -eq 0) {
    docker buildx build --load -t report:check .
  } else {
    docker compose build
  }
  if ($LASTEXITCODE -ne 0) { Write-Warning "Docker build failed (non-blocking)" }
} else {
  Write-Host "Docker not available, skipping" -ForegroundColor Yellow
}
Pop-Location

# 6. 版本号提升
Write-Host "=== Bumping version ===" -ForegroundColor Cyan
Push-Location $RootDir
if ($Version) {
  $newVersion = node scripts/bump-version.mjs --version $Version
} else {
  $newVersion = node scripts/bump-version.mjs $Level
}
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

# 12. 多平台镜像构建并推送至 GHCR
Push-Location $RootDir
if ($dockerAvailable) {
  $buildxAvailable = docker buildx version 2>$null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "=== Building multi-platform image ===" -ForegroundColor Cyan
    $imageRepo = $env:DOCKER_REGISTRY ?? "ghcr.io/virgooooox/report"
    docker buildx build `
      --platform linux/amd64,linux/arm64 `
      --push `
      -t "${imageRepo}:v$newVersion" `
      -t "${imageRepo}:latest" `
      .
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "Multi-platform build failed (non-blocking) - ensure you are logged into the registry"
    } else {
      Write-Host "Image pushed: ${imageRepo}:v$newVersion" -ForegroundColor Green
      Write-Host "Image pushed: ${imageRepo}:latest" -ForegroundColor Green
    }
  } else {
    Write-Host "Docker buildx not available, skipping multi-platform build" -ForegroundColor Yellow
  }
} else {
  Write-Host "Docker not available, skipping multi-platform build" -ForegroundColor Yellow
}
Pop-Location

# 13. 打印 Actions URL
Write-Host ""
Write-Host "=== Push complete ===" -ForegroundColor Green
Write-Host "Version: v$newVersion" -ForegroundColor Green
Write-Host "Actions: https://github.com/VirgoooooX/report/actions" -ForegroundColor Cyan

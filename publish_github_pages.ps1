param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,

    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

function Find-Git {
    $candidates = @(
        "git",
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "C:\Users\User\AppData\Local\Programs\Git\cmd\git.exe"
    )
    foreach ($candidate in $candidates) {
        try {
            $cmd = Get-Command $candidate -ErrorAction Stop
            return $cmd.Source
        } catch {
        }
    }
    throw "找不到 Git。請先安裝 Git for Windows。"
}

function Run-Git {
    param(
        [string]$GitExe,
        [string[]]$Args
    )
    & $GitExe @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Git 指令失敗: $($Args -join ' ')"
    }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$docsPath = Join-Path $root "docs"

if (-not (Test-Path $docsPath)) {
    throw "找不到 docs 資料夾，請先讓桌面版 GUI 更新一次快照。"
}

$gitExe = Find-Git
Write-Host "使用 Git: $gitExe"

$gitDir = Join-Path $root ".git"
if (-not (Test-Path $gitDir) -or -not (Test-Path (Join-Path $gitDir "HEAD"))) {
    Run-Git -GitExe $gitExe -Args @("init", "-b", $Branch, $root)
}

Run-Git -GitExe $gitExe -Args @("-C", $root, "add", ".github/workflows/deploy-github-pages.yml", "docs", "README_GITHUB_PAGES.md")

try {
    & $gitExe -C $root diff --cached --quiet
    $hasChanges = ($LASTEXITCODE -ne 0)
} catch {
    $hasChanges = $true
}

if ($hasChanges) {
    Run-Git -GitExe $gitExe -Args @("-C", $root, "commit", "-m", "Add GitHub Pages mobile snapshot")
} else {
    Write-Host "目前沒有新的變更需要 commit。"
}

try {
    & $gitExe -C $root remote get-url origin | Out-Null
    $hasOrigin = ($LASTEXITCODE -eq 0)
} catch {
    $hasOrigin = $false
}

if ($hasOrigin) {
    Run-Git -GitExe $gitExe -Args @("-C", $root, "remote", "set-url", "origin", $RepoUrl)
} else {
    Run-Git -GitExe $gitExe -Args @("-C", $root, "remote", "add", "origin", $RepoUrl)
}

Run-Git -GitExe $gitExe -Args @("-C", $root, "push", "-u", "origin", $Branch)

Write-Host ""
Write-Host "第一次發布已推送完成。"
Write-Host "接下來到 GitHub 專案 Settings -> Pages 確認來源為 GitHub Actions。"

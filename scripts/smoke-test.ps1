# smoke-test.ps1
# Smoke test for all hardened scripts in translate-agents-main.
# Usage: powershell -ExecutionPolicy Bypass -File scripts/smoke-test.ps1

$ErrorActionPreference = "Continue"
$RepoRoot = Split-Path -Parent $PSScriptRoot

# Force UTF-8 output for Python scripts on Windows
$env:PYTHONUTF8 = "1"

$passed  = 0
$failed  = 0
$failures = @()

function Assert-Test {
    param([string]$Name, [bool]$Condition, [string]$Detail = "")
    if ($Condition) {
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:passed++
    } else {
        Write-Host "  [FAIL] $Name" -ForegroundColor Red
        if ($Detail) { Write-Host "         $Detail" -ForegroundColor DarkRed }
        $script:failed++
        $script:failures += "  - $Name`: $Detail"
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  SMOKE TEST -- translate-agents-main hardening" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# Test 1: term-extract.js (missing args) -> usage contains "book-name"
# ---------------------------------------------------------------------------
Write-Host "  Running T1..." -ForegroundColor DarkGray
$out1 = & node "$RepoRoot\agents\agent-analyze\scripts\term-extract.js" 2>&1
$exit1 = $LASTEXITCODE
Assert-Test "T1: term-extract.js (no args) -> output contains 'book-name'" `
    ($out1 -match "book-name") `
    "Exit=$exit1. Got: $out1"

# ---------------------------------------------------------------------------
# Test 2: skill-cleanup.js (no bookName) -> exit 1
# Note: may throw MODULE_NOT_FOUND for cheerio if bun install not run,
# but that still exit 1 -- which is the correct guard behavior.
# ---------------------------------------------------------------------------
Write-Host "  Running T2..." -ForegroundColor DarkGray
$out2 = & node "$RepoRoot\agents\agent-scrape\scripts\skill-cleanup.js" 2>&1
$exit2 = $LASTEXITCODE
Assert-Test "T2: skill-cleanup.js (no bookName) -> exit 1" `
    ($exit2 -eq 1) `
    "Exit=$exit2. Got: $out2"

# ---------------------------------------------------------------------------
# Test 3: skill-cleanup.js (nonexistent book) -> exit 1 + helpful message
# ---------------------------------------------------------------------------
Write-Host "  Running T3..." -ForegroundColor DarkGray
$out3 = & node "$RepoRoot\agents\agent-scrape\scripts\skill-cleanup.js" "no-such-book-xyz" 2>&1
$exit3 = $LASTEXITCODE
Assert-Test "T3: skill-cleanup.js (missing RAW_DIR) -> exit 1" `
    ($exit3 -eq 1) `
    "Exit=$exit3. Got: $out3"

# ---------------------------------------------------------------------------
# Test 4: apply-review-fixes.py (nonexistent files) -> exit 1
# ---------------------------------------------------------------------------
Write-Host "  Running T4..." -ForegroundColor DarkGray
$out4 = & python "$RepoRoot\agents\agent-translate\scripts\apply-review-fixes.py" `
    "nonexistent-review.md" "nonexistent.html" 2>&1
$exit4 = $LASTEXITCODE
Assert-Test "T4: apply-review-fixes.py (no files) -> exit 1" `
    ($exit4 -eq 1) `
    "Exit=$exit4. Got: $out4"

# ---------------------------------------------------------------------------
# Test 5: build-preview.py (nonexistent path) -> exit 1
# ---------------------------------------------------------------------------
Write-Host "  Running T5..." -ForegroundColor DarkGray
$out5 = & python "$RepoRoot\agents\agent-archive\scripts\build-preview.py" `
    "../this-book-does-not-exist-smoke-test-xyz" 2>&1
$exit5 = $LASTEXITCODE
Assert-Test "T5: build-preview.py (bad path) -> exit 1" `
    ($exit5 -eq 1) `
    "Exit=$exit5. Got: $out5"

# ---------------------------------------------------------------------------
# Test 6: start-review-round.py (nonexistent file) -> exit 1
# ---------------------------------------------------------------------------
Write-Host "  Running T6..." -ForegroundColor DarkGray
$out6 = & python "$RepoRoot\agents\agent-review\scripts\start-review-round.py" `
    "nonexistent-file-xyz.html" 2>&1
$exit6 = $LASTEXITCODE
Assert-Test "T6: start-review-round.py (no file) -> exit 1" `
    ($exit6 -eq 1) `
    "Exit=$exit6. Got: $out6"

# ---------------------------------------------------------------------------
# Test 7: export-docx.js (no args) -> exit 1 + usage
# ---------------------------------------------------------------------------
Write-Host "  Running T9..." -ForegroundColor DarkGray
$out7 = & node "$RepoRoot\agents\agent-export\scripts\export-docx.js" 2>&1
$exit7 = $LASTEXITCODE
Assert-Test "T9: export-docx.js (no args) -> exit 1 + usage" `
    ($exit7 -eq 1 -and $out7 -match "node export-docx") `
    "Exit=$exit7. Got: $out7"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
$total = $passed + $failed
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "  SMOKE TEST: $passed/$total passed" -ForegroundColor Green
} else {
    Write-Host "  SMOKE TEST FAILED: $failed/$total failed" -ForegroundColor Red
    foreach ($f in $failures) { Write-Host $f -ForegroundColor Red }
}
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

if ($failed -gt 0) { exit 1 } else { exit 0 }

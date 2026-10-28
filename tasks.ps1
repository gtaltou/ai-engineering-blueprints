param (
    [Parameter(Position=0)]
    [ValidateSet("install", "lint", "typecheck", "test", "check", "clean")]
    [string]$Task = "check"
)

$ErrorActionPreference = "Stop"

function Run-Install {
    Write-Host "Installing package and development dependencies..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    pip install -e ".[dev]"
}

function Run-Lint {
    Write-Host "Running Ruff linter and formatter check..." -ForegroundColor Cyan
    ruff check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    ruff format --check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Run-Typecheck {
    Write-Host "Running strict Mypy static type checker..." -ForegroundColor Cyan
    mypy src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    mypy blueprints/01_structured_web_ingestion/pipeline.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    mypy blueprints/02_hybrid_rag_reranking/pipeline.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Run-Test {
    Write-Host "Running Pytest unit test suite..." -ForegroundColor Cyan
    pytest
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Run-Clean {
    Write-Host "Cleaning build, test, and cache artifacts..." -ForegroundColor Yellow
    $dirs = @("build", "dist", ".pytest_cache", ".mypy_cache", ".ruff_cache", "src/blueprint_core.egg-info")
    foreach ($d in $dirs) {
        if (Test-Path $d) { Remove-Item -Recurse -Force $d }
    }
}

switch ($Task) {
    "install"   { Run-Install }
    "lint"      { Run-Lint }
    "typecheck" { Run-Typecheck }
    "test"      { Run-Test }
    "clean"     { Run-Clean }
    "check"     {
        Write-Host "Running full quality gate (Lint + Format + Typecheck + Tests)..." -ForegroundColor Green
        Run-Lint
        Run-Typecheck
        Run-Test
        Write-Host "All quality checks passed!" -ForegroundColor Green
    }
}

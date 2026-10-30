param(
    [Parameter(Position=0)]
    [ValidateSet("install", "lint", "typecheck", "test", "check")]
    [string]$Task = "check"
)

$ErrorActionPreference = "Stop"
$VenvBin = ".\.venv\Scripts"

function Invoke-Install {
    Write-Host "Installing dependencies in editable mode..." -ForegroundColor Cyan
    & "$VenvBin\pip.exe" install -e ".[dev]"
}

function Invoke-Lint {
    Write-Host "Running Ruff linter and formatter check..." -ForegroundColor Cyan
    & "$VenvBin\ruff.exe" check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & "$VenvBin\ruff.exe" format --check .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Typecheck {
    Write-Host "Running strict Mypy static type checker..." -ForegroundColor Cyan
    & "$VenvBin\mypy.exe" src tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & "$VenvBin\mypy.exe" blueprints/01_structured_web_ingestion/pipeline.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & "$VenvBin\mypy.exe" blueprints/02_hybrid_rag_reranking/pipeline.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & "$VenvBin\mypy.exe" blueprints/03_agentic_tool_use_and_reflection/pipeline.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Test {
    Write-Host "Running Pytest unit test suite..." -ForegroundColor Cyan
    & "$VenvBin\pytest.exe"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

switch ($Task) {
    "install"   { Invoke-Install }
    "lint"      { Invoke-Lint }
    "typecheck" { Invoke-Typecheck }
    "test"      { Invoke-Test }
    "check"     {
        Write-Host "Running full quality gate (Lint + Format + Typecheck + Tests)..." -ForegroundColor Yellow
        Invoke-Lint
        Invoke-Typecheck
        Invoke-Test
        Write-Host "All quality checks passed!" -ForegroundColor Green
    }
}

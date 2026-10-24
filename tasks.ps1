param (
    [Parameter(Mandatory=$true)]
    [ValidateSet("install", "lint", "format", "typecheck", "test", "check", "run-bp01")]
    [string]$Task
)

$ErrorActionPreference = "Stop"

switch ($Task) {
    "install" {
        Write-Host "Installing package and dev dependencies in editable mode..." -ForegroundColor Cyan
        pip install -e ".[dev]"
    }
    "lint" {
        Write-Host "Running Ruff linter..." -ForegroundColor Cyan
        ruff check src/ blueprints/ tests/
    }
    "format" {
        Write-Host "Formatting code with Ruff..." -ForegroundColor Cyan
        ruff format src/ blueprints/ tests/
    }
    "typecheck" {
        Write-Host "Running strict static type checking with Mypy..." -ForegroundColor Cyan
        mypy src/ blueprints/
    }
    "test" {
        Write-Host "Running unit tests with Pytest..." -ForegroundColor Cyan
        pytest
    }
    "check" {
        Write-Host "Running full quality gate (Lint + Typecheck + Tests)..." -ForegroundColor Yellow
        ruff check src/ blueprints/ tests/
        mypy src/ blueprints/
        pytest
        Write-Host "All quality checks passed!" -ForegroundColor Green
    }
    "run-bp01" {
        Write-Host "Executing Blueprint 01: Structured Web Ingestion..." -ForegroundColor Cyan
        python blueprints/01_structured_web_ingestion/pipeline.py
    }
}

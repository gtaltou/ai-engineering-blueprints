param (
    [Parameter(Mandatory=$false)]
    [ValidateSet("install", "lint", "format", "typecheck", "test", "check", "clean")]
    [string]$Task = "check"
)

$ErrorActionPreference = "Stop"

switch ($Task) {
    "install" {
        Write-Host "Installing dependencies in editable mode..." -ForegroundColor Cyan
        python -m pip install -e ".[dev]"
    }
    "lint" {
        Write-Host "Running Ruff linter..." -ForegroundColor Cyan
        ruff check src tests blueprints
    }
    "format" {
        Write-Host "Formatting code with Ruff..." -ForegroundColor Cyan
        ruff format src tests blueprints
        ruff check --fix src tests blueprints
    }
    "typecheck" {
        Write-Host "Running strict Mypy type-checking..." -ForegroundColor Cyan
        mypy src tests
        Get-ChildItem -Path blueprints -Recurse -Filter *.py | ForEach-Object {
            mypy $_.FullName
        }
    }
    "test" {
        Write-Host "Running Pytest suite..." -ForegroundColor Cyan
        pytest
    }
    "check" {
        Write-Host "Running full quality gate (Lint + Typecheck + Tests)..." -ForegroundColor Yellow
        ruff check src tests blueprints
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        mypy src tests
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Get-ChildItem -Path blueprints -Recurse -Filter *.py | ForEach-Object {
            mypy $_.FullName
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        }
        pytest
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "All quality checks passed!" -ForegroundColor Green
    }
    "clean" {
        Write-Host "Cleaning build, test, and cache artifacts..." -ForegroundColor Cyan
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue .pytest_cache, .mypy_cache, .ruff_cache, .coverage, build, dist
        Get-ChildItem -Path . -Include __pycache__, *.egg-info -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    }
}

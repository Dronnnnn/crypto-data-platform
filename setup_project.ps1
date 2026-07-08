# ---------- src ----------
$folders = @(
    "src/common",
    "src/ingestion",
    "src/ingestion/clients",
    "src/ingestion/extractors",
    "src/transformations",
    "src/loaders",
    "src/models",

    "tests/unit",
    "tests/integration",

    "airflow/dags",
    "airflow/plugins",

    "spark/jobs",

    "data/sample",
    "data/tmp"
)

foreach ($folder in $folders) {
    New-Item -ItemType Directory -Force -Path $folder | Out-Null
}

# ---------- Python packages ----------
$initFiles = @(
    "src/common/__init__.py",
    "src/ingestion/__init__.py",
    "src/transformations/__init__.py",
    "src/loaders/__init__.py",
    "src/models/__init__.py"
)

foreach ($file in $initFiles) {
    if (!(Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
    }
}

# ---------- Common ----------
$commonFiles = @(
    "src/common/aws.py",
    "src/common/config.py",
    "src/common/logger.py",
    "src/common/utils.py"
)

foreach ($file in $commonFiles) {
    if (!(Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
    }
}

# ---------- Tests ----------
$testFiles = @(
    "tests/conftest.py"
)

foreach ($file in $testFiles) {
    if (!(Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
    }
}

# ---------- Root files ----------
$rootFiles = @(
    ".env.example",
    "README.md"
)

foreach ($file in $rootFiles) {
    if (!(Test-Path $file)) {
        New-Item -ItemType File -Path $file | Out-Null
    }
}

Write-Host ""
Write-Host "Project structure updated successfully." -ForegroundColor Green
param(
    [string]$RunDate = (Get-Date -Format 'yyyy-MM-dd'),
    [string]$Database = 'data/creator_ops.db',
    [switch]$TestOnly
)

$ErrorActionPreference = 'Stop'
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'

if ($pythonCommand) {
    $pythonExecutable = $pythonCommand.Source
} elseif (Test-Path -LiteralPath $bundledPython) {
    $pythonExecutable = $bundledPython
} else {
    throw 'Python 3.12 oder die gebündelte Codex-Python-Laufzeit wurde nicht gefunden.'
}

Push-Location $PSScriptRoot
try {
    & $pythonExecutable -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Tests fehlgeschlagen (Exitcode $LASTEXITCODE)."
    }

    if (-not $TestOnly) {
        & $pythonExecutable -m creator_ops.cli --db $Database evening-run --at "${RunDate}T20:00:00"
        if ($LASTEXITCODE -ne 0) {
            throw "Evening Run fehlgeschlagen (Exitcode $LASTEXITCODE)."
        }
        & $pythonExecutable -m creator_ops.cli --db $Database status
    }
} finally {
    Pop-Location
}

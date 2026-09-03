param(
    [string]$Database = 'data/review_dashboard.db',
    [int]$Port = 4180
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
    & $pythonExecutable -m creator_ops.web --db $Database --host 127.0.0.1 --port $Port
} finally {
    Pop-Location
}

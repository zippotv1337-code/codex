param([string]$Root='C:\Zippoworkz',[string]$Model='qwen2.5-coder:3b',[ValidateSet('Start','Pause','Resume','Stop','Status')][string]$Action='Start')
# v3.6: legacy entry point delegates to the maintained, bounded worker.
$entry = Join-Path $Root 'Workspace\codex_ingest\creator-collab\scripts\ai_ops\START_LOCAL_AI.ps1'
if (-not (Test-Path -LiteralPath $entry)) { throw 'Lokaler Bestand fehlt; kein ZIP-Austausch erlaubt.' }
& $entry -Root $Root -Model $Model -Action $Action

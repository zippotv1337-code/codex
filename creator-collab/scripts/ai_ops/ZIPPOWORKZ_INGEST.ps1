param([ValidateSet('VPS','LOCAL_AI')][string]$Mode='LOCAL_AI',[string]$Root='C:\Zippoworkz',[string]$Model='qwen3:8b')
if ($Mode -eq 'VPS') { throw 'VPS_NOT_CONNECTED: keine Remote-Ausführung vom Desktop vortäuschen.' }
& (Join-Path $Root '_system\ZIPPOWORKZ_LOCAL_AI_START.ps1') -Root $Root -Model $Model

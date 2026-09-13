@echo off
setlocal
title ZippoWorkz AI Ops
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0_system\ZIPPOWORKZ_LOCAL_AI_START.ps1"
if errorlevel 1 (
  echo Start fehlgeschlagen. Siehe C:\Zippoworkz\Logs.
  pause
  exit /b 1
)
start "" "http://192.168.188.131:4180/ai-ops"
exit /b 0

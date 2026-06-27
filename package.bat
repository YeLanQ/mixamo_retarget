@echo off
echo Creating Mixamo Retarget package...
powershell -ExecutionPolicy Bypass -File "%~dp0package.ps1"
pause

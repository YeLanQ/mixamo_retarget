@echo off
echo Creating Mixamo Retarget package...
powershell -ExecutionPolicy Bypass -File "%~dp0create_package.ps1"
pause

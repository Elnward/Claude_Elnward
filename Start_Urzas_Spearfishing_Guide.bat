@echo off
cd /d "%~dp0"
set PYTHONDONTWRITEBYTECODE=1

where python >nul 2>nul
if %errorlevel%==0 (
    python Start_Urzas_Spearfishing_Guide.py %*
    goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
    py Start_Urzas_Spearfishing_Guide.py %*
    goto :end
)

echo Es wurde kein Python gefunden ^(weder "python" noch "py" im PATH^).
echo Bitte Python 3.10 oder neuer installieren: https://www.python.org/downloads/
echo Beim Installieren unbedingt "Add python.exe to PATH" ankreuzen.
pause
exit /b 1

:end
if errorlevel 1 pause

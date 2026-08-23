@echo off
setlocal
title IuPetra Local Observatory
echo ==========================================
echo IuPetra Local Observatory
echo ==========================================
echo Running resilient data pull, reports, viewers, and dashboard...
echo.

python run_iupetra.py
set EXITCODE=%ERRORLEVEL%

if exist "reports\00_START_HERE\IuPetra_START_HERE.html" (
    start "" "reports\00_START_HERE\IuPetra_START_HERE.html"
)

echo.
if %EXITCODE% EQU 0 (
    echo IuPetra finished successfully.
) else (
    echo IuPetra reported an error. Review:
    echo reports\99_TECHNICAL_LOGS\error_log.txt
)

echo.
echo Dashboard:
echo reports\00_START_HERE\IuPetra_START_HERE.html
echo Provenance:
echo reports\99_TECHNICAL_LOGS\run_provenance.json
pause
exit /b %EXITCODE%

@echo off
title IuPetra Local Observatory
echo ==========================================
echo IuPetra Local Observatory
echo ==========================================
echo Running data pull, reports, viewers, and dashboard...
echo.
python iupetra.py
if exist "reports\00_START_HERE\IuPetra_START_HERE.html" start "" "reports\00_START_HERE\IuPetra_START_HERE.html"
echo.
echo Done. If the dashboard did not open, use:
echo reports\00_START_HERE\IuPetra_START_HERE.html
pause

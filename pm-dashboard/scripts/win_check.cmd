@echo off
setlocal EnableDelayedExpansion
title PM Dashboard - check the extracted files
color 0F

set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"

echo.
echo  ============================================================
echo   Checking the extracted Power BI project
echo  ============================================================
echo.
echo  Folder: %SRC%
echo.

set "BAD=0"

call :want "PM_Dashboard.pbip"                                   "project entry point"
call :want "PM_Dashboard.SemanticModel\definition.pbism"         "semantic model properties"
call :want "PM_Dashboard.SemanticModel\definition\model.tmdl"    "model definition"
call :want "PM_Dashboard.Report\definition.pbir"                 "report properties"
call :want "PM_Dashboard.Report\definition\report.json"          "report definition"
call :want "PM_Dashboard.Report\definition\pages\pages.json"     "page list"
call :want "data\Cell_Master.csv"                                "sample data"
call :want "theme\PM_Theme.json"                                 "theme"

set /a TMDL=0
for /f %%A in ('dir /b /s "%SRC%\PM_Dashboard.SemanticModel\definition\tables\*.tmdl" 2^>nul ^| find /c /v ""') do set TMDL=%%A
set /a VIS=0
for /f %%A in ('dir /b /s "%SRC%\PM_Dashboard.Report\definition\pages\visual.json" 2^>nul ^| find /c /v ""') do set VIS=%%A
set /a PAGES=0
for /f %%A in ('dir /b /ad "%SRC%\PM_Dashboard.Report\definition\pages\pg*" 2^>nul ^| find /c /v ""') do set PAGES=%%A
set /a CSV=0
for /f %%A in ('dir /b "%SRC%\data\*.csv" 2^>nul ^| find /c /v ""') do set CSV=%%A

echo.
echo   table files (expect __NTMDL__) : !TMDL!
echo   report pages (expect __NPAGES__): !PAGES!
echo   visuals (expect __NVIS__)    : !VIS!
echo   CSV files (expect __NCSV__)   : !CSV!

if !TMDL! LSS __NTMDL__ set BAD=1
if !PAGES! LSS __NPAGES__ set BAD=1
if !VIS! LSS __NVIS__ set BAD=1
if !CSV! LSS __NCSV__ set BAD=1

echo.
if "%BAD%"=="1" (
  echo  ------------------------------------------------------------
  echo   FILES ARE MISSING.
  echo  ------------------------------------------------------------
  echo.
  echo   The usual cause is opening the project from inside the zip.
  echo   Windows extracts only the file you double-clicked, so the
  echo   rest of the project is not there and Desktop reports a
  echo   "Required artifact is missing" error.
  echo.
  echo   Fix: right-click the zip ^> Extract All ^> choose a real
  echo   folder such as C:\PM_Dashboard, then run this again from
  echo   the extracted copy.
) else (
  echo  ------------------------------------------------------------
  echo   All present. Extraction is complete.
  echo  ------------------------------------------------------------
  echo.
  echo   Open PM_Dashboard.pbip. If Desktop still refuses it, the
  echo   wrapper files do not match your build - run INSTALL.cmd,
  echo   which lets Desktop write those files itself.
)
echo.
pause
endlocal
goto :eof

:want
if exist "%SRC%\%~1" (
  echo   [ok]      %~2
) else (
  echo   [MISSING] %~2   ^(%~1^)
  set BAD=1
)
goto :eof

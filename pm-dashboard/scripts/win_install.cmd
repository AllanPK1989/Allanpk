@echo off
setlocal EnableDelayedExpansion
title PM Dashboard - install into a Power BI project
color 0F

set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"

echo.
echo  ============================================================
echo   PM Dashboard - install into a Power BI project
echo  ============================================================
echo.
echo  This copies the semantic model and the 10 report pages into a
echo  project that Power BI Desktop created itself. Desktop writes the
echo  small wrapper files, which are the ones that differ between
echo  versions, so this works whatever build you are on.
echo.
echo  BEFORE RUNNING THIS:
echo.
echo    1. Open Power BI Desktop.
echo    2. File ^> Options and settings ^> Options ^> Preview features.
echo       Tick: Power BI Project (.pbip) save option
echo             Store semantic model using TMDL format
echo             Enhanced report format (PBIR)
echo       Restart Desktop if you changed any of them.
echo    3. Get data ^> Text/CSV ^> pick any file from the data folder
echo       next to this script ^> Load.
echo    4. File ^> Save as ^> Power BI project (.pbip)
echo       Name it exactly:  PM_Dashboard
echo       Save it into a NEW EMPTY FOLDER, for example C:\PM_Dashboard
echo    5. CLOSE Power BI Desktop completely.
echo.
echo  ------------------------------------------------------------
echo.

set "TARGET="
set /p "TARGET=Full path to that new folder (e.g. C:\PM_Dashboard): "
rem %%~P strips surrounding quotes safely; the usual set-substitution trick
rem breaks when the value itself contains a quote character.
for /f "tokens=* delims=" %%P in ("%TARGET%") do set "TARGET=%%~P"
if defined TARGET if "!TARGET:~-1!"=="\" set "TARGET=!TARGET:~0,-1!"

if "%TARGET%"=="" (
  echo.
  echo  [X] No folder given. Nothing has been changed.
  goto :done
)
if not exist "%TARGET%\" (
  echo.
  echo  [X] That folder does not exist: %TARGET%
  goto :done
)
if not exist "%TARGET%\PM_Dashboard.pbip" (
  echo.
  echo  [X] No PM_Dashboard.pbip in that folder.
  echo      Save the blank project there first, named exactly PM_Dashboard.
  goto :done
)
if not exist "%TARGET%\PM_Dashboard.SemanticModel\definition\" (
  echo.
  echo  [X] No PM_Dashboard.SemanticModel\definition folder found.
  echo      The TMDL preview feature was probably off when you saved.
  echo      Turn on "Store semantic model using TMDL format", restart,
  echo      save the blank project again, then re-run this.
  goto :done
)
if not exist "%TARGET%\PM_Dashboard.Report\definition\pages\" (
  echo.
  echo  [X] No PM_Dashboard.Report\definition\pages folder found.
  echo      The PBIR preview feature was probably off when you saved.
  echo      Turn on "Enhanced report format (PBIR)", restart, save the
  echo      blank project again, then re-run this.
  goto :done
)

echo.
echo  Installing into: %TARGET%
echo.

robocopy "%SRC%\PM_Dashboard.SemanticModel\definition" "%TARGET%\PM_Dashboard.SemanticModel\definition" /E /PURGE /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail
echo   [ok] semantic model   __NTABLES__ tables, __NMEAS__ measures, __NREL__ relationships

robocopy "%SRC%\PM_Dashboard.Report\definition\pages" "%TARGET%\PM_Dashboard.Report\definition\pages" /E /PURGE /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail
echo   [ok] report pages     __NPAGES__ pages, __NVIS__ visuals

robocopy "%SRC%\data" "%TARGET%\data" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail
echo   [ok] sample data      __NCSV__ CSV files

robocopy "%SRC%\theme" "%TARGET%\theme" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail
echo   [ok] theme            PM_Theme.json

echo.
echo  ------------------------------------------------------------
echo   Done. Desktop's own wrapper files were left untouched.
echo  ------------------------------------------------------------
echo.
echo   NEXT:
echo     1. Open %TARGET%\PM_Dashboard.pbip
echo     2. Home ^> Transform data ^> Manage parameters
echo        Set LocalDataFolder to:  %TARGET%\data
echo     3. Close and apply, then Home ^> Refresh
echo     4. View ^> Themes ^> Browse for themes ^> %TARGET%\theme\PM_Theme.json
echo.
echo   The blank query Desktop made when you loaded a CSV is still
echo   there. Delete it in Transform data once the refresh works.
echo.
goto :done

:copyfail
echo.
echo  [X] A copy failed. The usual cause is Power BI Desktop still
echo      being open, which locks the files. Close it and re-run.

:done
echo.
pause
endlocal

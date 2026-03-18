@echo off
REM Build VoxWave pour Windows
REM Usage: scripts\build_windows.bat [clean|build|package|installer|all]
REM
REM Commandes:
REM   build     - Compile l'exe avec PyInstaller
REM   installer - Cree l'installer avec Inno Setup (necessite build d'abord)
REM   all       - Clean + Build + Package + Installer
REM   clean     - Supprime les artefacts
REM   package   - Cree le ZIP de distribution

echo ========================================
echo  VoxWave Build Script (Windows)
echo ========================================

cd /d "%~dp0\.."

if "%1"=="" (
    python build.py all
) else (
    python build.py %1
)

if errorlevel 1 (
    echo.
    echo BUILD FAILED
    pause
    exit /b 1
)

echo.
echo BUILD SUCCESS
pause

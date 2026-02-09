@echo off
REM Build VoxTool pour Windows
REM Usage: scripts\build_windows.bat [clean|build|package|all]

echo ========================================
echo  VoxTool Build Script (Windows)
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

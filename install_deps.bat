@echo off
REM Tungsten Video Editor - Dependency Installer (Batch)
REM ====================================================

echo Tungsten Video Editor - Dependency Installer
echo ============================================
echo.

REM Check Python version
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.10+ from https://python.org
    echo.
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing runtime dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install runtime dependencies
    pause
    exit /b 1
)

echo Installing development dependencies...
pip install -r requirements-dev.txt
if errorlevel 1 (
    echo ERROR: Failed to install development dependencies
    pause
    exit /b 1
)

echo.
echo ============================================
echo Installation complete!
echo ============================================
echo.
echo To run the application:
echo   .venv\Scripts\activate.bat
echo   python main.py
echo.
echo To build the portable executable:
echo   .venv\Scripts\activate.bat
echo   python build_exe.py
echo.
pause
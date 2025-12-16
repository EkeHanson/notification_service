@echo off
REM Notification Service Test Runner for Windows
REM This script activates the virtual environment and runs tests

echo Activating virtual environment...
call venv\Scripts\activate.bat

if %ERRORLEVEL% neq 0 (
    echo Failed to activate virtual environment
    exit /b 1
)

echo Running tests...
python tests/run_tests.py %*

echo.
echo Tests completed.
pause
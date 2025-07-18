:: This batch file sets up a user's environment to build the Context Keeper plugin
@echo off
setlocal

:: Determine if we have 'python' or 'python3' in the path. On Windows, the
:: Python executable is typically called 'python', so check that first.
where /q python
if ERRORLEVEL 1 goto python3
set PYTHON=python
goto checkversion

:python3
where /q python3
if ERRORLEVEL 1 goto nopython
set PYTHON=python3

:: Check Python version (requires 3.12+)
:checkversion
echo Checking Python version...
%PYTHON% -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"
if ERRORLEVEL 1 (
    echo Error: Python 3.12 or higher is required
    echo Found Python version:
    %PYTHON% --version
    exit /b 1
)

:: Setup the virtual environment if it does not already exist
:setup
set VENV=..\venv
if not exist %VENV% (
    echo Creating virtual environment...
    %PYTHON% -m venv %VENV%
) else (
    echo Using existing virtual environment at %VENV%
)

:: Install/upgrade pip first
echo.
echo Activating virtual environment and upgrading pip...
call %VENV%\Scripts\activate.bat
%PYTHON% -m pip install --upgrade pip

:: Install the required packages
echo.
echo Installing required packages...
%PYTHON% -m pip install -r requirements.txt

:: Install pyinstaller for building
echo.
echo Installing PyInstaller for building...
%PYTHON% -m pip install pyinstaller

call %VENV%\Scripts\deactivate.bat

echo.
echo Setup complete!
echo.
echo To test the plugin, activate the virtual environment with:
echo   %VENV%\Scripts\activate.bat
echo.
echo Then run tests with:
echo   python test_context_keeper.py
echo.
echo Or try the demo with:
echo   python demo_usage.py

endlocal
exit /b 0

:nopython
echo Python needs to be installed and in your path
echo Please install Python 3.12 or higher from https://www.python.org/
exit /b 1
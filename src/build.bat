:: This batch file converts the Context Keeper plugin into a Windows executable
@echo off
setlocal

:: Determine if we have 'python' or 'python3' in the path. On Windows, the
:: Python executable is typically called 'python', so check that first.
where /q python
if ERRORLEVEL 1 goto python3
set PYTHON=python
goto build

:python3
where /q python3
if ERRORLEVEL 1 goto nopython
set PYTHON=python3

:: Verify the setup script has been run
:build
set VENV=..\venv
set DIST_DIR=dist
set PLUGIN_NAME=context-keeper
set PLUGIN_DIR=%DIST_DIR%\%PLUGIN_NAME%

if exist %VENV% (
    echo Activating virtual environment...
    call %VENV%\Scripts\activate.bat

    :: Clean previous builds
    if exist build rmdir /s /q build
    if exist %DIST_DIR% rmdir /s /q %DIST_DIR%

    :: Ensure dist directory exists
    if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%"

    :: Build the executable with all dependencies
    echo.
    echo Building Context Keeper plugin...
    pyinstaller --onefile ^
        --name %PLUGIN_NAME% ^
        --distpath "%PLUGIN_DIR%" ^
        --add-data "manifest.json;." ^
        --hidden-import=win32com.client ^
        --hidden-import=pycaw ^
        --hidden-import=comtypes ^
        --hidden-import=pywinauto ^
        --hidden-import=lz4 ^
        --exclude-module=matplotlib ^
        --exclude-module=numpy ^
        --exclude-module=pandas ^
        --exclude-module=scipy ^
        --exclude-module=tkinter ^
        --exclude-module=PyQt5 ^
        --exclude-module=PySide2 ^
        plugin.py

    :: Copy manifest.json
    if exist manifest.json (
        copy /y manifest.json "%PLUGIN_DIR%\manifest.json"
        echo manifest.json copied successfully.
    ) else (
        echo Warning: manifest.json not found!
    )

    :: Copy any additional required files
    if exist README.md (
        copy /y README.md "%PLUGIN_DIR%\README.md"
        echo README.md copied successfully.
    )

    :: Create a simple batch launcher for testing
    echo @echo off > "%PLUGIN_DIR%\run-context-keeper.bat"
    echo echo Starting Context Keeper Plugin... >> "%PLUGIN_DIR%\run-context-keeper.bat"
    echo %PLUGIN_NAME%.exe >> "%PLUGIN_DIR%\run-context-keeper.bat"
    echo pause >> "%PLUGIN_DIR%\run-context-keeper.bat"

    call %VENV%\Scripts\deactivate.bat

    :: Display build info
    echo.
    echo =================================================
    echo Build completed successfully!
    echo =================================================
    echo.
    echo Executable location: %PLUGIN_DIR%\%PLUGIN_NAME%.exe
    echo.
    echo Files in distribution folder:
    dir /b "%PLUGIN_DIR%"
    echo.
    echo To test the plugin:
    echo   1. Copy the entire "%PLUGIN_DIR%" folder to your G-Assist plugins directory
    echo   2. Or run directly: %PLUGIN_DIR%\%PLUGIN_NAME%.exe
    echo.

    exit /b 0
) else (
    echo Error: Virtual environment not found!
    echo Please run setup.bat before attempting to build
    exit /b 1
)

:nopython
echo Python needs to be installed and in your path
echo Please install Python 3.12 or higher from https://www.python.org/
exit /b 1
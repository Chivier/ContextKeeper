:: This batch file builds a debug version of the Keeper plugin
@echo off
setlocal

:: Determine if we have 'python' or 'python3' in the path
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
set VENV=..\..\venv
set DIST_DIR=dist_debug
set PLUGIN_NAME=g-assist-plugin-keeper-debug
set PLUGIN_DIR=%DIST_DIR%\keeper

if exist %VENV% (
    echo Activating virtual environment...
    call %VENV%\Scripts\activate.bat

    :: Clean previous builds
    if exist build rmdir /s /q build
    if exist %DIST_DIR% rmdir /s /q %DIST_DIR%

    :: Ensure dist directory exists
    if not exist "%PLUGIN_DIR%" mkdir "%PLUGIN_DIR%"

    :: Build the debug executable with console window
    echo.
    echo Building Keeper plugin (DEBUG version with console)...
    pyinstaller --onefile ^
        --console ^
        --name %PLUGIN_NAME% ^
        --distpath "%PLUGIN_DIR%" ^
        --add-data "..\manifest.json;." ^
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
        --debug=all ^
        plugin_debug_wrapper.py

    :: Copy manifest.json from parent directory
    if exist ..\manifest.json (
        copy /y ..\manifest.json "%PLUGIN_DIR%\manifest.json"
        echo manifest.json copied successfully.
    ) else (
        echo Warning: manifest.json not found in parent directory!
    )

    :: Copy test scripts
    copy /y test_plugin_communication.py "%PLUGIN_DIR%\"
    copy /y validate_memorize.py "%PLUGIN_DIR%\"

    :: Create debug info file
    echo Debug Build Information > "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo ====================== >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo. >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo Built on: %date% %time% >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo. >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo This is a DEBUG build with console output enabled. >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo. >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo Log files will be created at: >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo - %%USERPROFILE%%\keeper_plugin.log >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo - %%USERPROFILE%%\keeper_plugin_debug.log >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo - %%USERPROFILE%%\.keeper\debug\session_*.log >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo. >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo To test communication: >> "%PLUGIN_DIR%\DEBUG_INFO.txt"
    echo python test_plugin_communication.py >> "%PLUGIN_DIR%\DEBUG_INFO.txt"

    call %VENV%\Scripts\deactivate.bat

    :: Display build info
    echo.
    echo =================================================
    echo Debug build completed successfully!
    echo =================================================
    echo.
    echo Debug executable: %PLUGIN_DIR%\%PLUGIN_NAME%.exe
    echo.
    echo Files in debug distribution:
    dir /b "%PLUGIN_DIR%"
    echo.
    echo This debug build includes:
    echo - Console window for real-time output
    echo - Enhanced logging to multiple files
    echo - Test scripts for validation
    echo.
    echo Check log files at:
    echo - %%USERPROFILE%%\keeper_plugin.log
    echo - %%USERPROFILE%%\keeper_plugin_debug.log
    echo - %%USERPROFILE%%\.keeper\debug\session_*.log
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
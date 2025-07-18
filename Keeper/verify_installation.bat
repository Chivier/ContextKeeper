@echo off
echo ========================================
echo Context Keeper Plugin Installation Check
echo ========================================
echo.

set PLUGIN_DIR=%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins\context-keeper

echo Checking G-Assist plugin directory...
echo Expected location: %PLUGIN_DIR%
echo.

if exist "%PLUGIN_DIR%" (
    echo [OK] Plugin directory exists
    echo.
    echo Contents:
    dir /b "%PLUGIN_DIR%"
    echo.
    
    if exist "%PLUGIN_DIR%\manifest.json" (
        echo [OK] manifest.json found
    ) else (
        echo [ERROR] manifest.json NOT FOUND!
    )
    
    if exist "%PLUGIN_DIR%\g-assist-plugin-contextkeeper.exe" (
        echo [OK] g-assist-plugin-contextkeeper.exe found
    ) else (
        echo [ERROR] g-assist-plugin-contextkeeper.exe NOT FOUND!
    )
) else (
    echo [ERROR] Plugin directory does NOT exist!
    echo.
    echo Creating directory...
    mkdir "%PLUGIN_DIR%"
    echo Directory created. Please copy plugin files here.
)

echo.
echo ========================================
echo Checking other G-Assist plugins...
echo ========================================
echo.

set PLUGINS_ROOT=%PROGRAMDATA%\NVIDIA Corporation\nvtopps\rise\plugins
if exist "%PLUGINS_ROOT%" (
    echo Other plugins installed:
    dir /b "%PLUGINS_ROOT%"
) else (
    echo [WARNING] No plugins directory found at all!
    echo G-Assist may not be properly installed.
)

echo.
echo ========================================
echo Installation Instructions:
echo ========================================
echo.
echo 1. Build the plugin:
echo    cd %~dp0
echo    build.bat
echo.
echo 2. Copy to G-Assist:
echo    xcopy /E /Y "dist\context-keeper" "%PLUGIN_DIR%\"
echo.
echo 3. Restart G-Assist completely
echo.
echo 4. Test with these commands:
echo    - "save workspace as test"
echo    - "list workspaces"
echo    - "quick save"
echo.
pause
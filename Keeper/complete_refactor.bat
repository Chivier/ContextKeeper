@echo off
echo ======================================
echo Keeper Refactoring Script
echo ======================================
echo.
echo This script will help complete the refactoring from context-keeper to Keeper.
echo.

:: Create new directory structure
echo Creating new Keeper directory structure...
cd ..
if not exist "Keeper" mkdir Keeper

:: Copy all files from context-keeper to Keeper
echo Copying files to new Keeper directory...
xcopy /E /I /Y "context-keeper\*.*" "Keeper\"

:: Update remaining references in copied files
echo Updating references in the new directory...
cd Keeper

:: Update Python files
powershell -Command "(Get-Content 'environment_manager.py') -replace 'context_keeper', 'keeper' | Set-Content 'environment_manager.py'"
powershell -Command "(Get-Content 'windows_context_manager.py') -replace 'context_keeper', 'keeper' | Set-Content 'windows_context_manager.py'"
powershell -Command "(Get-Content 'test_keeper.py') -replace 'context_keeper', 'keeper' -replace 'ContextKeeper', 'Keeper' | Set-Content 'test_keeper.py'"
powershell -Command "(Get-Content 'test_plugin_direct.py') -replace 'context_keeper', 'keeper' -replace 'ContextKeeper', 'Keeper' | Set-Content 'test_plugin_direct.py'"
powershell -Command "(Get-Content 'demo_usage.py') -replace 'context_keeper', 'keeper' -replace 'ContextKeeper', 'Keeper' | Set-Content 'demo_usage.py'"

:: Update the installation path in documentation
powershell -Command "(Get-Content 'README.md') -replace 'contextkeeper', 'keeper' | Set-Content 'README.md'"

:: Rename spec files if they weren't already renamed
if exist "context-keeper.spec" ren "context-keeper.spec" "keeper.spec"
if exist "g-assist-plugin-contextkeeper.spec" ren "g-assist-plugin-contextkeeper.spec" "g-assist-plugin-keeper.spec"

:: Update spec file contents
if exist "keeper.spec" (
    powershell -Command "(Get-Content 'keeper.spec') -replace 'context-keeper', 'keeper' -replace 'contextkeeper', 'keeper' | Set-Content 'keeper.spec'"
)
if exist "g-assist-plugin-keeper.spec" (
    powershell -Command "(Get-Content 'g-assist-plugin-keeper.spec') -replace 'contextkeeper', 'keeper' | Set-Content 'g-assist-plugin-keeper.spec'"
)

echo.
echo ======================================
echo Refactoring Summary
echo ======================================
echo.
echo 1. Created new Keeper directory with all files
echo 2. Updated all references from context-keeper to Keeper
echo 3. Renamed spec files
echo 4. Updated executable name to g-assist-plugin-keeper.exe
echo.
echo Next Steps:
echo -----------
echo 1. Test the build process: cd Keeper && build.bat
echo 2. Update G-Assist to point to the new Keeper directory
echo 3. Delete the old context-keeper directory when ready
echo.
echo Note: The old context-keeper directory is preserved for backup.
echo.
pause
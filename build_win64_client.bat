@echo off

SET "SRCDIR=%~dp0src\"
SET "CONDA_ENV_PATH=%USERPROFILE%\.conda\envs\pyguibank"
SET "CONDA_PATH=%USERPROFILE%\miniconda3\Scripts\activate.bat"
SET "CONDA_ENV=pyguibank"

:: Navigate to the project src directory
cd /d %~dp0

:: Activate the conda environment
call "%CONDA_PATH%" %CONDA_ENV%
if ERRORLEVEL 1 (
    echo ERROR: Failed to activate conda environment.
    set ERRORS=1
    goto :error_exit
)

:: Shortcuts
::goto :nsis_installer
::goto :deploy

:: Build the executable
pyinstaller ^
    --clean ^
    --noconfirm ^
    --noconsole ^
    -n "PyGuiBank" ^
    --workpath "prebuild" ^
    --distpath "build" ^
    --paths %SRCDIR% ^
    --add-data "assets;assets" ^
    --hidden-import=openpyxl.cell._writer ^
    --hidden-import=scipy._lib.array_api_compat.numpy.fft ^
    --hidden-import=scipy.special._special_ufuncs ^
    --splash "assets\pyguibank_base.png" ^
    --icon "assets\pyguibank_128px.ico" ^
    "%SRCDIR%main.py"

if ERRORLEVEL 1 (
    echo ERROR: Failed to build the executable.
    set ERRORS=1
    goto :error_exit
)

:nsis_installer
:: Create Install Package at dist\pyguibank_version_win64_setup.exe
mkdir dist\win64 2>NUL
for /f "tokens=2 delims== " %%A in ('findstr "^__version__" "src\version.py"') do (
    set VERSION=%%~A
)
set VERSION=%VERSION:"=%
makensis /V4 -DVERSION="%VERSION%" .\scripts\win64_installer.nsi

if ERRORLEVEL 1 (
    echo ERROR: Failed to create the install package.
    set ERRORS=1
    goto :error_exit
)

:: Deactivate the conda environment
call conda deactivate

:deploy
:: Deploy the installer to the server
echo Deploying installer to server
set SCRIPT_PATH=/mnt/c/Users/tbrow/dev/pyguibank/scripts/deploy_win64_client.sh
wsl /bin/sh %SCRIPT_PATH%

:: Exit without error
@echo Script execution completed successfully!
pause
exit /b 0

:: Exit with errors
:error_exit
echo Script encountered errors and is exiting.
pause
exit /b !ERRORS!

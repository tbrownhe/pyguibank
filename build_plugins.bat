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

:: Compile plugins and copy into dist\plugins
python .\src\build_plugins.py
if ERRORLEVEL 1 (
    echo ERROR: Failed to compile plugins.
    set ERRORS=1
    goto :error_exit
)

:deploy
:: Deploy the plugins to the server
echo Deploying plugins to server
set SCRIPT_PATH=/mnt/c/Users/tbrow/dev/pyguibank/scripts/deploy_plugins.sh
wsl /bin/sh %SCRIPT_PATH%

if ERRORLEVEL 1 (
    echo ERROR: Failed to deploy plugins.
    set ERRORS=1
    goto :error_exit
)

:: Exit without error
pause
exit

:: Exit with errors
:error_exit
echo Script encountered errors and is exiting.
pause
exit /b !ERRORS!

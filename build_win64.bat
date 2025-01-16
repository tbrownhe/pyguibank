@echo off

set SERVER_DIR=..\pyguibank-server\data\clients\win64

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
    --splash "assets\pyguibank.png" ^
    --icon "assets\pyguibank.png" ^
    "%SRCDIR%main.py"

if ERRORLEVEL 1 (
    echo ERROR: Failed to build the executable.
    set ERRORS=1
    goto :error_exit
)

:: Create Install Package as dist\pyguibank_version_setup.exe
makensis /V4 .\scripts\win64_installer.nsi

if ERRORLEVEL 1 (
    echo ERROR: Failed to create the install package.
    set ERRORS=1
    goto :error_exit
)

:: Rename the file with the version.py version
for /f "tokens=2 delims== " %%A in ('findstr "^__version__" "src\version.py"') do (
    set VERSION=%%~A
)
set VERSION=%VERSION:"=%
set INSTALLER_NAME=pyguibank_%VERSION%_win64_setup.exe
ren "dist\pyguibank_version_win64_setup.exe" "%INSTALLER_NAME%"
if ERRORLEVEL 1 (
    echo ERROR: Failed to rename the installer.
    set ERRORS=1
    goto :error_exit
)

:: Copy final installer to server data
if not exist "%SERVER_DIR%" (
    mkdir "%SERVER_DIR%"
)
copy "dist\%INSTALLER_NAME%" "%SERVER_DIR%\"
if errorlevel 1 (
    echo Failed to copy the installer to the server directory.
    exit /b 1
) else (
    echo Installer successfully copied to %SERVER_DIR%.
)

:: Deactivate the conda environment
call conda deactivate

@echo Script execution completed successfully!
pause
exit /b 0


:error_exit
echo Script encountered errors and is exiting.
pause
exit /b !ERRORS!

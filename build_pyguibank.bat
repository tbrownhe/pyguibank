@echo off

SET "PROJ_DIR=%~dp0"
SET "SRCDIR=%PROJ_DIR%src\"
SET "CONDA_ENV_PATH=%USERPROFILE%\.conda\envs\pyguibank"
SET "CONDA_PATH=%USERPROFILE%\miniconda3\Scripts\activate.bat"
SET "CONDA_ENV=pyguibank"

REM Navigate to the project src directory
cd /d %PROJ_DIR%

REM Activate the conda environment
call "%CONDA_PATH%" %CONDA_ENV%

REM Build the executable
pyinstaller ^
    --clean ^
    --noconfirm ^
    --noconsole ^
    -n "PyGuiBank" ^
    --distpath "%~dp0\dist" ^
    --workpath "%~dp0\build" ^
    --paths %SRCDIR% ^
    --add-data "%PROJ_DIR%config.ini;." ^
    --add-data "%PROJ_DIR%init_db.json;." ^
    --add-data "%PROJ_DIR%pyguibank.png;." ^
    --add-data "%PROJ_DIR%pipeline.mdl;." ^
    --add-data "%PROJ_DIR%pyguibank.db;." ^
    --hidden-import=openpyxl.cell._writer ^
    --hidden-import=scipy._lib.array_api_compat.numpy.fft ^
    --hidden-import=scipy.special._special_ufuncs ^
    --splash "%PROJ_DIR%pyguibank.png" ^
    --icon "%PROJ_DIR%pyguibank.png" ^
    "%SRCDIR%pyguibank.py"

REM Some useful flags:
REM --log-level=DEBUG ^
REM --debug imports ^
REM --noconsole ^

REM Deactivate the conda environment
call conda deactivate

@echo Script execution completed!
pause
@echo off

SET "SRCDIR=%~dp0src\"
SET "CONDA_ENV_PATH=%USERPROFILE%\.conda\envs\pyguibank"
SET "CONDA_PATH=%USERPROFILE%\miniconda3\Scripts\activate.bat"
SET "CONDA_ENV=pyguibank"

REM Navigate to the project src directory
cd /d %~dp0

REM Activate the conda environment
call "%CONDA_PATH%" %CONDA_ENV%

REM 
python -m compileall src\plugins

REM Compile plugins and copy into dist\plugins
python move_plugins.py

REM Build the executable
pyinstaller ^
    --clean ^
    --noconfirm ^
    --noconsole ^
    -n "PyGuiBank" ^
    --workpath "build" ^
    --distpath "dist" ^
    --paths %SRCDIR% ^
    --add-data "config.ini;." ^
    --add-data "init_db.json;." ^
    --add-data "init_accounts.json;." ^
    --add-data "pyguibank.png;." ^
    --add-data "pipeline.mdl;." ^
    --add-data "dist\plugins;plugins" ^
    --add-data "pyguibank.db;." ^
    --hidden-import=openpyxl.cell._writer ^
    --hidden-import=scipy._lib.array_api_compat.numpy.fft ^
    --hidden-import=scipy.special._special_ufuncs ^
    --splash "pyguibank.png" ^
    --icon "pyguibank.png" ^
    "%SRCDIR%pyguibank.py"

REM Some useful flags:
REM --log-level=DEBUG ^
REM --debug imports ^

REM Create Install Package as dist\pyguibank_version_setup.exe
makensis /V4 pyguibank_setup.nsi

REM Deactivate the conda environment
call conda deactivate

@echo Script execution completed!
pause
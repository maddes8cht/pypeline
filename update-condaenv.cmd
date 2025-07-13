@echo off
:: Standard-Requirements-Datei setzen, falls kein Argument übergeben wird
set REQUIREMENTS_FILE=requirements.yml
if not "%~1"=="" set REQUIREMENTS_FILE=%~1

:: Lese den ENV_NAME aus der YAML-Datei
for /f "tokens=2 delims=: " %%A in ('findstr /i "name:" %REQUIREMENTS_FILE%') do set ENV_NAME=%%A

echo Using Requirements File: %REQUIREMENTS_FILE%
echo Environment Name: %ENV_NAME%

echo Updating conda environment %ENV_NAME% with %REQUIREMENTS_FILE%...
conda env update --name %ENV_NAME% --file %REQUIREMENTS_FILE%

if %errorlevel% neq 0 (
    echo Error: Failed to update conda environment.
    exit /b %errorlevel%
)

echo Running PyTorch test...
python pytorch-test.py

echo update completed successfully!
@echo off
:: Standard-Requirements-Datei setzen, falls kein Argument übergeben wird
set REQUIREMENTS_FILE=requirements.yml
if not "%~1"=="" set REQUIREMENTS_FILE=%~1

:: Lese den ENV_NAME aus der YAML-Datei
for /f "tokens=2 delims=: " %%A in ('findstr /i "name:" %REQUIREMENTS_FILE%') do set ENV_NAME=%%A

echo Using Requirements File: %REQUIREMENTS_FILE%
echo Environment Name: %ENV_NAME%

echo Deactivate the environment...
call mamba deactivate

echo Delete the environment %ENV_NAME%...
call mamba env remove -n %ENV_NAME% -y

echo Clean the Mamba cache...
call mamba clean --all -y

echo Recreate the environment from %REQUIREMENTS_FILE%...
call mamba env create --file %REQUIREMENTS_FILE%
if %errorlevel% neq 0 (
    echo ERROR: Environment creation failed. Please check for dependency conflicts.
    exit /b 1
)

:: Prüfen, ob das Environment existiert
mamba env list | findstr /i "%ENV_NAME%" >nul
if %errorlevel% neq 0 (
    echo ERROR: Environment %ENV_NAME% not found after installation.
    exit /b 1
)

echo Environment %ENV_NAME% has been successfully created!

echo Activate the environment %ENV_NAME%...
call mamba activate %ENV_NAME%

echo Setup completed successfully!

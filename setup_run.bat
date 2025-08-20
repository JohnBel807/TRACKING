@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === Ir a la carpeta del script ===
cd /d "%~dp0"

echo [1/5] Creando entorno virtual (.venv) si no existe...
if not exist .venv\Scripts\python.exe (
    python -m venv .venv
)

if not exist .venv\Scripts\activate.bat (
    echo Error: No se pudo crear el entorno virtual. ^(Revisa que Python este en PATH^).
    pause & exit /b 1
)

echo [2/5] Activando entorno...
call .venv\Scripts\activate.bat

echo [3/5] Actualizando pip...
python -m pip install --upgrade pip

if exist requirements.txt (
    echo [4/5] Instalando dependencias de requirements.txt...
    pip install -r requirements.txt
) else (
    echo Advertencia: No se encontro requirements.txt. Instalando dependencias minimas...
    pip install Flask pandas numpy openpyxl
)

if not exist instance (
    mkdir instance
)

echo [5/5] Iniciando la aplicacion Flask...
python app.py

endlocal

@echo off
REM =============================================================================
REM Intranet Dashboard - Script de inicio para Windows
REM =============================================================================
REM Activa el entorno virtual y ejecuta la aplicación Flask
REM =============================================================================

echo.
echo ========================================
echo   Intranet Dashboard - Iniciando...
echo ========================================
echo.

REM Verificar si existe el entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] No se encontro el entorno virtual.
    echo Ejecuta primero: python -m venv venv
    echo.
    pause
    exit /b 1
)

REM Activar entorno virtual
echo [1/3] Activando entorno virtual...
call venv\Scripts\activate.bat

REM Verificar que .env existe
if not exist ".env" (
    echo [WARN] Archivo .env no encontrado.
    echo Copia .env.example a .env y configura tus variables.
    echo.
)

REM Ejecutar aplicación
echo [2/3] Cargando variables de entorno...
echo [3/3] Iniciando servidor Flask...
echo.
echo ========================================
echo   Dashboard: http://localhost:5000
echo   Ctrl+C para detener
echo ========================================
echo.

python app.py

REM Si llegamos aquí, la app se detuvo
echo.
echo [INFO] Servidor detenido.
pause

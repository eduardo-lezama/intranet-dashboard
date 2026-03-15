#!/bin/bash
# =============================================================================
# Intranet Dashboard - Script de inicio para Linux/Mac
# =============================================================================
# Activa el entorno virtual y ejecuta la aplicación Flask
# =============================================================================

echo ""
echo "========================================"
echo "  Intranet Dashboard - Iniciando..."
echo "========================================"
echo ""

# Verificar si existe el entorno virtual
if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] No se encontró el entorno virtual."
    echo "Ejecuta primero: python -m venv venv"
    echo ""
    exit 1
fi

# Activar entorno virtual
echo "[1/3] Activando entorno virtual..."
source venv/bin/activate

# Verificar que .env existe
if [ ! -f ".env" ]; then
    echo "[WARN] Archivo .env no encontrado."
    echo "Copia .env.example a .env y configura tus variables."
    echo ""
fi

# Ejecutar aplicación
echo "[2/3] Cargando variables de entorno..."
echo "[3/3] Iniciando servidor Flask..."
echo ""
echo "========================================"
echo "  Dashboard: http://localhost:5000"
echo "  Ctrl+C para detener"
echo "========================================"
echo ""

python app.py

# Si llegamos aquí, la app se detuvo
echo ""
echo "[INFO] Servidor detenido."

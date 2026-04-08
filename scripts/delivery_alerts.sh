#!/bin/bash
# filepath: /code/scripts/delivery_alerts.sh

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="/var/log/delivery_alerts.log"
ERROR_LOG="/var/log/delivery_alerts_error.log"

# Función de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "🚀 Iniciando proceso de alertas de entrega..."

# Cambiar al directorio del proyecto
cd "$PROJECT_DIR" || {
    log "❌ Error: No se pudo acceder al directorio $PROJECT_DIR"
    exit 1
}

# Activar entorno virtual si existe
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    log "✅ Entorno virtual activado"
fi

# Verificar conectividad de red
if ping -c 1 mail.2asoft.tech > /dev/null 2>&1; then
    log "✅ Conectividad al servidor de email verificada"
else
    log "⚠️ Advertencia: No se puede alcanzar el servidor de email"
fi

# Ejecutar comando con reintentos
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    log "📧 Intento de envío #$((RETRY_COUNT + 1))"
    
    if python manage.py notify_delivery_deadlines --days=7 2>>"$ERROR_LOG"; then
        log "✅ Alertas enviadas exitosamente"
        exit 0
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            WAIT_TIME=$((RETRY_COUNT * 30))
            log "❌ Error en intento #$RETRY_COUNT, reintentando en ${WAIT_TIME}s..."
            sleep $WAIT_TIME
        fi
    fi
done

log "❌ Error: Falló después de $MAX_RETRIES intentos"
exit 1
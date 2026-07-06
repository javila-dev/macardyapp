#!/bin/sh
set -e

PGHOST="${DB_HOST:-central-postgres}"
PGPORT="${DB_PORT:-5432}"
PGUSER="${DB_USER:-mcduser}"
PGPASSWORD="${DB_PASSWORD:?DB_PASSWORD is required}"
export PGPASSWORD

DB_SOURCE_NAME="${DB_SOURCE_NAME:-macardyapp}"
PRODUCTION_DB_NAME="${PRODUCTION_DB_NAME:-macardyapp}"
PG_MAINTENANCE_DB="${PG_MAINTENANCE_DB:-postgres}"
DUMP_PATH="/tmp/staging-refresh.dump"

psql_maintenance() {
    psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PG_MAINTENANCE_DB" -v ON_ERROR_STOP=1 "$@"
}

echo "=== MacardyApp STAGING entrypoint ==="

if [ -z "${DB_NAME:-}" ]; then
    echo "ERROR: DB_NAME is required for staging."
    exit 1
fi

if [ "$DB_NAME" = "$PRODUCTION_DB_NAME" ]; then
    echo "ERROR: DB_NAME must not be the production database ($PRODUCTION_DB_NAME)."
    exit 1
fi

case "$DB_NAME" in
    *staging*) ;;
    *)
        echo "ERROR: DB_NAME must contain 'staging' (current: $DB_NAME)."
        exit 1
        ;;
esac

if [ "$DB_SOURCE_NAME" = "$DB_NAME" ]; then
    echo "ERROR: DB_SOURCE_NAME and DB_NAME must be different."
    exit 1
fi

database_exists() {
    psql_maintenance -tAc "SELECT 1 FROM pg_database WHERE datname = '$1'" | grep -q 1
}

create_staging_database_if_missing() {
    if database_exists "$DB_NAME"; then
        return 0
    fi

    echo "Creating empty staging database: $DB_NAME"
    if psql_maintenance -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$PGUSER\";"; then
        return 0
    fi

    echo "ERROR: Cannot create database '$DB_NAME' (permission denied)."
    echo "Create it once in pgAdmin, then redeploy:"
    echo "  CREATE DATABASE macardyapp_staging OWNER mcduser;"
    exit 1
}

ensure_staging_database() {
    create_staging_database_if_missing
}

disconnect_staging_sessions() {
    if ! database_exists "$DB_NAME"; then
        return 0
    fi

    echo "Closing active connections to $DB_NAME..."
    attempt=1
    while [ "$attempt" -le 10 ]; do
        psql_maintenance -c "
            REVOKE CONNECT ON DATABASE \"$DB_NAME\" FROM PUBLIC;
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '$DB_NAME'
              AND pid <> pg_backend_pid();
        " >/dev/null 2>&1 || true

        active_sessions=$(psql_maintenance -tAc "
            SELECT COUNT(*)
            FROM pg_stat_activity
            WHERE datname = '$DB_NAME'
              AND pid <> pg_backend_pid();
        " 2>/dev/null || echo "1")

        if [ "${active_sessions:-1}" = "0" ]; then
            return 0
        fi

        echo "Waiting for ${active_sessions} session(s) on $DB_NAME to close (attempt $attempt/10)..."
        sleep 2
        attempt=$((attempt + 1))
    done

    echo "WARNING: Could not close all sessions on $DB_NAME."
}

refresh_staging_database() {
    echo "Refreshing staging database: $DB_SOURCE_NAME -> $DB_NAME"

    if ! database_exists "$DB_SOURCE_NAME"; then
        echo "ERROR: Source database '$DB_SOURCE_NAME' does not exist."
        exit 1
    fi

    create_staging_database_if_missing
    disconnect_staging_sessions

    echo "Running pg_dump from $DB_SOURCE_NAME..."
    pg_dump \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$DB_SOURCE_NAME" \
        -Fc \
        --no-owner \
        --no-acl \
        -f "$DUMP_PATH"

    echo "Running pg_restore into $DB_NAME (in-place refresh)..."
    set +e
    pg_restore \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$DB_NAME" \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        "$DUMP_PATH"
    restore_exit=$?
    set -e

    psql_maintenance -c "GRANT CONNECT ON DATABASE \"$DB_NAME\" TO PUBLIC;" >/dev/null 2>&1 || true

    rm -f "$DUMP_PATH"

    if [ "$restore_exit" -gt 1 ]; then
        echo "ERROR: pg_restore failed with exit code $restore_exit."
        exit "$restore_exit"
    fi

    if [ "$restore_exit" -eq 1 ]; then
        echo "WARNING: pg_restore finished with non-fatal warnings."
    fi

    echo "Staging database refresh completed."
}

case "${REFRESH_STAGING_DB:-false}" in
    true|1|yes|YES)
        refresh_staging_database
        ;;
    *)
        echo "Skipping DB refresh (set REFRESH_STAGING_DB=true to clone from production)."
        ensure_staging_database
        ;;
esac

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Starting STAGING application..."
if [ $# -eq 0 ]; then
    echo "ERROR: No startup command (gunicorn). Check docker-compose command/CMD."
    exit 1
fi
exec "$@"

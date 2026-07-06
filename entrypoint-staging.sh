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

ensure_staging_database() {
    if database_exists "$DB_NAME"; then
        return 0
    fi

    echo "Creating empty staging database: $DB_NAME"
    psql_maintenance -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$PGUSER\";"
}

refresh_staging_database() {
    echo "Refreshing staging database: $DB_SOURCE_NAME -> $DB_NAME"

    if ! database_exists "$DB_SOURCE_NAME"; then
        echo "ERROR: Source database '$DB_SOURCE_NAME' does not exist."
        exit 1
    fi

    echo "Terminating active connections to $DB_NAME..."
    psql_maintenance -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '$DB_NAME'
          AND pid <> pg_backend_pid();
    " >/dev/null 2>&1 || true

    echo "Recreating staging database..."
    psql_maintenance -c "DROP DATABASE IF EXISTS \"$DB_NAME\";"
    psql_maintenance -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$PGUSER\";"

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

    echo "Running pg_restore into $DB_NAME..."
    set +e
    pg_restore \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$PGUSER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        "$DUMP_PATH"
    restore_exit=$?
    set -e

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
exec "$@"

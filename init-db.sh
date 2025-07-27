#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE golfcart;
    GRANT ALL PRIVILEGES ON DATABASE golfcart TO $POSTGRES_USER;
EOSQL
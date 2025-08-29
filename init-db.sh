#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Create application schema
    CREATE SCHEMA IF NOT EXISTS golfcart;
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA golfcart TO $POSTGRES_USER;
EOSQL
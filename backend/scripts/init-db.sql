-- Initialize tenant_management database

-- Create database if it doesn't exist (this runs automatically in docker-entrypoint-initdb.d)
-- CREATE DATABASE tenant_management;

-- Connect to the database
\c tenant_management;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE tenant_management TO postgres;

-- Add any additional initialization SQL here
SELECT 'Database initialized successfully!' AS status;

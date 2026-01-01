# Database Setup Guide

This guide explains how to set up and manage the PostgreSQL database for the Tenant Management Portal.

## Quick Start with Docker Compose

The easiest way to get started is using Docker Compose, which sets up PostgreSQL and pgAdmin automatically.

### 1. Start PostgreSQL

```bash
cd backend
docker-compose up -d
```

This starts:
- **PostgreSQL** on port `5432`
- **pgAdmin** (database UI) on port `5050`

### 2. Verify Database is Running

```bash
docker-compose ps
```

You should see both `postgres` and `pgadmin` containers running.

### 3. Run Database Migrations

```bash
# From the backend directory
alembic upgrade head
```

This creates all the necessary tables (tenants, schedules, audit_logs, user_permissions).

### 4. Seed Sample Data (Optional)

```bash
python scripts/init_db.py
```

This creates:
- 3 demo tenants
- 3 sample schedules
- Sample user permissions

### 5. Start the Backend

```bash
uvicorn app.main:app --reload
```

Your API is now running at `http://localhost:8000` with a fully configured database!

---

## Manual PostgreSQL Setup

If you prefer to install PostgreSQL directly on your machine:

### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download from https://www.postgresql.org/download/windows/

### 2. Create Database

```bash
# Connect to PostgreSQL
psql postgres

# Create database and user
CREATE DATABASE tenant_management;
CREATE USER tenant_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE tenant_management TO tenant_user;
\q
```

### 3. Update .env File

```bash
cp .env.example .env
```

Edit `.env` and update the database URL:
```
DATABASE_URL=postgresql+asyncpg://tenant_user:your_secure_password@localhost:5432/tenant_management
```

### 4. Run Migrations

```bash
alembic upgrade head
```

---

## Database Management Commands

### Alembic Migration Commands

```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Upgrade to latest version
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>

# Downgrade to base (drop all tables)
alembic downgrade base

# Create new migration (auto-generate from models)
alembic revision --autogenerate -m "description of changes"

# Create empty migration
alembic revision -m "description of changes"
```

### Database Scripts

```bash
# Seed sample data
python scripts/init_db.py

# Reset database (WARNING: deletes all data)
python scripts/reset_db.py
```

---

## Database Access

### Using pgAdmin (Web UI)

1. Open http://localhost:5050 in your browser
2. Login with:
   - Email: `admin@example.com`
   - Password: `admin`
3. Add server:
   - Name: `Tenant Management`
   - Host: `postgres` (or `localhost` if not using Docker)
   - Port: `5432`
   - Database: `tenant_management`
   - Username: `postgres`
   - Password: `postgres`

### Using psql (Command Line)

```bash
# Connect to database
psql -h localhost -U postgres -d tenant_management

# Common queries
\dt              # List all tables
\d tenants       # Describe tenants table
SELECT * FROM tenants;
SELECT * FROM schedules;
SELECT * FROM audit_logs;
```

---

## Database Schema

### Tables

1. **tenants** - Stores tenant information
   - id, name, namespace, deployment_name
   - status, current_replicas, desired_replicas
   - created_at, updated_at, last_scaled_at, last_scaled_by

2. **schedules** - Stores automated schedules
   - id, tenant_id, action, cron_expression
   - enabled, description
   - last_run_at, next_run_at, last_run_status

3. **audit_logs** - Stores all user actions
   - id, tenant_id, action, user_id, user_name
   - success, error_message, details
   - ip_address, user_agent, created_at

4. **user_permissions** - Maps users to tenants with roles
   - id, user_id, tenant_id, role
   - created_at, updated_at, granted_by

### Relationships

- Tenant → Schedules (one-to-many)
- Tenant → AuditLogs (one-to-many)
- Tenant → UserPermissions (one-to-many)

---

## Troubleshooting

### Connection Refused

**Error:** `could not connect to server: Connection refused`

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps
# or
brew services list | grep postgresql

# Restart PostgreSQL
docker-compose restart postgres
# or
brew services restart postgresql@16
```

### Database Already Exists

**Error:** `database "tenant_management" already exists`

This is fine! Just run migrations:
```bash
alembic upgrade head
```

### Migration Conflicts

**Error:** `Can't locate revision identified by 'xxxxx'`

**Solution:**
```bash
# Check current version
alembic current

# Stamp to current version
alembic stamp head

# Or reset migrations
alembic downgrade base
alembic upgrade head
```

### Permission Denied

**Error:** `permission denied for schema public`

**Solution:**
```sql
-- Connect to database and grant permissions
psql -h localhost -U postgres -d tenant_management
GRANT ALL PRIVILEGES ON SCHEMA public TO tenant_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tenant_user;
```

---

## Environment Variables

Key database-related environment variables in `.env`:

```bash
# Database Connection
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tenant_management
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Environment
APP_ENV=development
DEBUG=true
```

---

## Production Considerations

### Database Backups

```bash
# Backup database
docker exec tenant-management-db pg_dump -U postgres tenant_management > backup.sql

# Restore database
docker exec -i tenant-management-db psql -U postgres tenant_management < backup.sql
```

### Connection Pooling

For production, consider:
- Using PgBouncer for connection pooling
- Increasing `DATABASE_POOL_SIZE` based on load
- Using a managed database service (AWS RDS, Azure Database, etc.)

### Security

- Change default passwords in production
- Use environment variables for sensitive data
- Enable SSL for database connections
- Restrict database access by IP
- Regular security updates

### Monitoring

- Enable slow query logging
- Monitor connection pool usage
- Set up alerts for database errors
- Regular performance analysis

---

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgAdmin Documentation](https://www.pgadmin.org/docs/)

"""Database initialization and seed data script"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import Tenant, Schedule, UserPermission
from app.models.tenant import TenantStatus
from app.models.schedule import ScheduleAction
from app.models.user_permission import UserRole


async def seed_data():
    """Seed initial data into the database"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if data already exists
            result = await session.execute(select(Tenant))
            existing_tenants = result.scalars().all()
            
            if existing_tenants:
                print("⚠️  Database already contains data. Skipping seed.")
                return

            print("📦 Seeding database with sample data...")

            # Create sample tenants
            tenants = [
                Tenant(
                    name="tenant-demo-001",
                    namespace="tenant-demo-001",
                    deployment_name="demo-001-app",
                    description="Demo tenant for development",
                    status=TenantStatus.RUNNING,
                    current_replicas=2,
                    desired_replicas=2,
                ),
                Tenant(
                    name="tenant-demo-002",
                    namespace="tenant-demo-002",
                    deployment_name="demo-002-app",
                    description="Demo tenant for testing",
                    status=TenantStatus.STOPPED,
                    current_replicas=0,
                    desired_replicas=1,
                ),
                Tenant(
                    name="tenant-demo-003",
                    namespace="tenant-demo-003",
                    deployment_name="demo-003-app",
                    description="Demo tenant for staging",
                    status=TenantStatus.RUNNING,
                    current_replicas=1,
                    desired_replicas=1,
                ),
            ]

            session.add_all(tenants)
            await session.flush()  # Get IDs for relationships

            print(f"✅ Created {len(tenants)} sample tenants")

            # Create sample schedules
            schedules = [
                Schedule(
                    tenant_id=tenants[0].id,
                    action=ScheduleAction.STOP,
                    cron_expression="0 18 * * 1-5",  # 6 PM Mon-Fri
                    description="Stop at 6 PM on weekdays",
                    enabled=True,
                    created_by="system",
                ),
                Schedule(
                    tenant_id=tenants[0].id,
                    action=ScheduleAction.START,
                    cron_expression="0 8 * * 1-5",  # 8 AM Mon-Fri
                    description="Start at 8 AM on weekdays",
                    enabled=True,
                    created_by="system",
                ),
                Schedule(
                    tenant_id=tenants[1].id,
                    action=ScheduleAction.START,
                    cron_expression="0 9 * * 1-5",  # 9 AM Mon-Fri
                    description="Start at 9 AM on weekdays",
                    enabled=False,
                    created_by="system",
                ),
            ]

            session.add_all(schedules)
            print(f"✅ Created {len(schedules)} sample schedules")

            # Create sample user permissions
            permissions = [
                UserPermission(
                    user_id="admin@example.com",
                    tenant_id=tenants[0].id,
                    role=UserRole.ADMIN,
                    granted_by="system",
                ),
                UserPermission(
                    user_id="admin@example.com",
                    tenant_id=tenants[1].id,
                    role=UserRole.ADMIN,
                    granted_by="system",
                ),
                UserPermission(
                    user_id="admin@example.com",
                    tenant_id=tenants[2].id,
                    role=UserRole.ADMIN,
                    granted_by="system",
                ),
                UserPermission(
                    user_id="operator@example.com",
                    tenant_id=tenants[0].id,
                    role=UserRole.OPERATOR,
                    granted_by="admin@example.com",
                ),
            ]

            session.add_all(permissions)
            print(f"✅ Created {len(permissions)} sample user permissions")

            await session.commit()
            print("✅ Database seeded successfully!")

        except Exception as e:
            print(f"❌ Error seeding database: {e}")
            await session.rollback()
            raise


async def main():
    """Main function"""
    print("🚀 Starting database initialization...")
    await seed_data()
    print("✅ Database initialization complete!")


if __name__ == "__main__":
    asyncio.run(main())

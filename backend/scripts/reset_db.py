"""Database reset script - drops all tables and recreates them"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine, Base
from app.models import Tenant, Schedule, AuditLog, UserPermission


async def reset_database():
    """Drop all tables and recreate them"""
    print("⚠️  WARNING: This will delete ALL data in the database!")
    confirmation = input("Type 'yes' to continue: ")
    
    if confirmation.lower() != 'yes':
        print("❌ Operation cancelled")
        return

    try:
        print("🗑️  Dropping all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ All tables dropped")

        print("🔨 Creating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ All tables created")

        print("✅ Database reset complete!")

    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(reset_database())

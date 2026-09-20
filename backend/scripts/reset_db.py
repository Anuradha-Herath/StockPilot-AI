import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text
from app.core.database import async_engine, AsyncSessionLocal
from app.db.base import Base
from app.db.init_db import seed_database


async def reset_database():
    """
    Drops all application tables and recreates them from metadata,
    then executes the supermarket domain seed data routine.
    """
    print("WARNING: Resetting database (dropping all tables)...")
    async with async_engine.begin() as conn:
        # Drop all tables cleanly with CASCADE
        await conn.run_sync(Base.metadata.drop_all)
        print("All existing tables dropped.")
        
        # Recreate tables
        await conn.run_sync(Base.metadata.create_all)
        print("All tables recreated successfully.")

    print("Seeding fresh supermarket domain data...")
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    print("Database reset and initial seed complete!")


if __name__ == "__main__":
    asyncio.run(reset_database())

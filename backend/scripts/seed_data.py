import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.init_db import run_seed

if __name__ == "__main__":
    print("Starting StockPilot AI Database Seed...")
    asyncio.run(run_seed())
    print("Database seeding completed.")

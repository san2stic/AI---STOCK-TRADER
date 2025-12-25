"""
Script to reset the database by dropping all tables and recreating them.
WARNING: This will delete all data in the database!
"""
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, init_db
from models.database import Base
from models.crew_models import (
    CrewSession, AgentMessage, CrewVote, CrewPerformance
)
from models.economic_event import EconomicEvent
import structlog

logger = structlog.get_logger()

def reset_database():
    print("⚠️  WARNING: This will DELETE ALL DATA in the database.")
    confirm = input("Are you sure you want to proceed? (y/n): ")
    
    if confirm.lower() != 'y':
        print("Operation cancelled.")
        return

    print("\n1. Dropping all tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✓ All tables dropped successfully.")
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        return

    print("\n2. Reinitializing database...")
    try:
        init_db()
        print("✓ Database reinitialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return

    print("\n✨ Database reset complete!")

if __name__ == "__main__":
    reset_database()

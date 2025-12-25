"""
Create database migration for crypto support.
Run this after updating the database.py models.
"""
from database import init_db

if __name__ == "__main__":
    print("Creating database tables with crypto support...")
    init_db()
    print("✓ Database migration complete!")
    print("✓ Crypto trading support enabled")

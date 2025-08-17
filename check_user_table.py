#!/usr/bin/env python3
"""
Check the actual structure of the users table in the database
"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import get_db_session

async def check_user_table():
    """Check the actual structure of the users table"""
    try:
        session = await get_db_session()
        
        try:
            # Get table structure
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            
            if not columns:
                print("❌ Users table does not exist!")
                return False
                
            print("✅ Users table structure:")
            print("-" * 60)
            print(f"{'Column Name':<20} {'Data Type':<15} {'Nullable':<10} {'Default'}")
            print("-" * 60)
            
            for col in columns:
                column_name, data_type, is_nullable, column_default = col
                nullable = "YES" if is_nullable == "YES" else "NO"
                default = str(column_default) if column_default else "None"
                print(f"{column_name:<20} {data_type:<15} {nullable:<10} {default}")
                
            # Check if we can create a simple user
            print("\n✅ Users table exists and is accessible!")
            return True
            
        finally:
            await session.close()
            
    except Exception as e:
        print(f"❌ Error checking users table: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(check_user_table())
    sys.exit(0 if success else 1)

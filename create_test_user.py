#!/usr/bin/env python3
"""
Create a test user and validate authentication system
"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import get_db_session
from app.core.security import get_password_hash, verify_password

async def create_test_user():
    """Create a test user for authentication testing"""
    try:
        session = await get_db_session()
        
        try:
            # Test user data
            email = "test@codebegen.com"
            username = "testuser"
            password = "test123"
            hashed_password = get_password_hash(password)
            
            # Check if user already exists
            result = await session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email}
            )
            existing_user = result.fetchone()
            
            if existing_user:
                print(f"✅ Test user {email} already exists!")
                user_id = existing_user[0]
            else:
                # Create new user
                import uuid
                user_id = str(uuid.uuid4())
                
                await session.execute(text("""
                    INSERT INTO users (
                        id, email, username, hashed_password, 
                        is_active, is_superuser, is_verified, total_generations,
                        created_at, updated_at
                    ) VALUES (
                        :id, :email, :username, :hashed_password,
                        :is_active, :is_superuser, :is_verified, :total_generations,
                        NOW(), NOW()
                    )
                """), {
                    "id": user_id,
                    "email": email,
                    "username": username,
                    "hashed_password": hashed_password,
                    "is_active": True,
                    "is_superuser": False,
                    "is_verified": True,
                    "total_generations": 0
                })
                
                await session.commit()
                print(f"✅ Created test user: {email}")
            
            # Verify password hashing works
            test_verify = verify_password(password, hashed_password)
            if test_verify:
                print("✅ Password hashing and verification working!")
            else:
                print("❌ Password verification failed!")
                return False
                
            # Get the created user details
            result = await session.execute(
                text("SELECT id, email, username, is_active, is_verified FROM users WHERE email = :email"),
                {"email": email}
            )
            user = result.fetchone()
            
            print(f"\n🎯 Test User Details:")
            print(f"   ID: {user[0]}")
            print(f"   Email: {user[1]}")
            print(f"   Username: {user[2]}")
            print(f"   Active: {user[3]}")
            print(f"   Verified: {user[4]}")
            print(f"   Password: {password}")
            
            print(f"\n✅ Database schema setup complete!")
            print(f"✅ Test user ready for authentication testing!")
            return True
            
        finally:
            await session.close()
            
    except Exception as e:
        print(f"❌ Error creating test user: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(create_test_user())
    sys.exit(0 if success else 1)

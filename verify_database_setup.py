#!/usr/bin/env python3
"""
Database Schema Verification and Test User Creation
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from passlib.context import CryptContext

# Add the app directory to Python path
sys.path.append('.')

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def verify_database_schema():
    """Verify that the database schema is correctly set up"""
    print("🔍 Verifying Database Schema...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if users table exists and has the correct columns
            result = await session.execute(
                text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                ORDER BY ordinal_position;
                """)
            )
            
            columns = result.fetchall()
            if not columns:
                print("❌ Users table not found!")
                return False
                
            print("✅ Users table found with columns:")
            for col in columns:
                print(f"   - {col.column_name}: {col.data_type} ({'NULL' if col.is_nullable == 'YES' else 'NOT NULL'})")
            
            # Check for required authentication columns
            column_names = [col.column_name for col in columns]
            required_cols = ['id', 'email', 'hashed_password', 'is_active', 'is_verified']
            
            missing_cols = [col for col in required_cols if col not in column_names]
            if missing_cols:
                print(f"❌ Missing required columns: {missing_cols}")
                return False
            
            print("✅ All required authentication columns present")
            return True
            
        except Exception as e:
            print(f"❌ Error checking database schema: {e}")
            return False

async def check_existing_users():
    """Check if there are any existing users in the database"""
    print("\n👥 Checking existing users...")
    
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
            
            if count == 0:
                print("📝 No users found in database")
                return []
            
            # Get existing users
            result = await session.execute(
                text("SELECT id, email, username, is_active, is_verified FROM users LIMIT 5")
            )
            users = result.fetchall()
            
            print(f"✅ Found {count} users in database:")
            for user in users:
                print(f"   - ID: {user.id}, Email: {user.email}, Username: {user.username}, Active: {user.is_active}")
            
            return users
            
        except Exception as e:
            print(f"❌ Error checking existing users: {e}")
            return []

async def create_test_user():
    """Create a test user for API testing"""
    print("\n🧪 Creating test user...")
    
    test_email = "test@codebegen.com"
    test_username = "testuser"
    test_password = "test123"
    
    async with AsyncSessionLocal() as session:
        try:
            # Check if test user already exists
            result = await session.execute(
                text("SELECT id FROM users WHERE email = :email OR username = :username"),
                {"email": test_email, "username": test_username}
            )
            existing = result.fetchone()
            
            if existing:
                print(f"✅ Test user already exists (ID: {existing.id})")
                return existing.id
            
            # Create new test user
            hashed_password = pwd_context.hash(test_password)
            
            # Using raw SQL to ensure compatibility
            result = await session.execute(
                text("""
                INSERT INTO users (id, created_at, updated_at, email, username, hashed_password, 
                                 is_active, is_superuser, is_verified, total_generations)
                VALUES (gen_random_uuid()::text, NOW(), NOW(), :email, :username, :password, 
                       true, false, true, 0)
                RETURNING id, email, username
                """),
                {
                    "email": test_email,
                    "username": test_username, 
                    "password": hashed_password
                }
            )
            
            user = result.fetchone()
            await session.commit()
            
            print(f"✅ Test user created successfully!")
            print(f"   - ID: {user.id}")
            print(f"   - Email: {user.email}")
            print(f"   - Username: {user.username}")
            print(f"   - Password: {test_password}")
            
            return user.id
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating test user: {e}")
            return None

async def test_authentication_flow():
    """Test the authentication flow"""
    print("\n🔐 Testing Authentication Flow...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Test password verification
            test_email = "test@codebegen.com"
            test_password = "test123"
            
            result = await session.execute(
                text("SELECT id, email, hashed_password, is_active FROM users WHERE email = :email"),
                {"email": test_email}
            )
            user = result.fetchone()
            
            if not user:
                print("❌ Test user not found for authentication test")
                return False
            
            # Verify password
            password_valid = pwd_context.verify(test_password, user.hashed_password)
            
            if password_valid and user.is_active:
                print("✅ Authentication flow working correctly")
                print(f"   - User ID: {user.id}")
                print(f"   - Email: {user.email}")
                print(f"   - Active: {user.is_active}")
                return True
            else:
                print("❌ Authentication failed")
                return False
                
        except Exception as e:
            print(f"❌ Error testing authentication: {e}")
            return False

async def main():
    """Main verification function"""
    print("🚀 Database Schema Verification & User Setup")
    print("=" * 50)
    
    # Step 1: Verify database schema
    schema_ok = await verify_database_schema()
    if not schema_ok:
        print("❌ Database schema verification failed!")
        return
    
    # Step 2: Check existing users
    existing_users = await check_existing_users()
    
    # Step 3: Create test user if needed
    test_user_id = await create_test_user()
    if not test_user_id:
        print("❌ Failed to create test user!")
        return
    
    # Step 4: Test authentication flow
    auth_ok = await test_authentication_flow()
    if not auth_ok:
        print("❌ Authentication flow test failed!")
        return
    
    print("\n🎉 Database Setup Complete!")
    print("=" * 50)
    print("✅ Database schema verified")
    print("✅ User table properly configured")
    print("✅ Test user created/verified")
    print("✅ Authentication flow working")
    print("\n📝 Test User Credentials:")
    print("   Email: test@codebegen.com")
    print("   Username: testuser") 
    print("   Password: test123")
    print("\n🚀 Ready for API testing!")

if __name__ == "__main__":
    asyncio.run(main())

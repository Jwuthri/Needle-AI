#!/usr/bin/env python3
"""
Test Redis connection with SSL support.
Usage: python scripts/test-redis.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.redis_client import RedisClient
from app.utils.logging import get_logger

logger = get_logger("redis_test")


async def test_redis_connection():
    """Test Redis connection and basic operations."""
    print("🔍 Testing Redis connection...\n")
    
    client = RedisClient()
    
    try:
        # Test connection
        print("1️⃣  Connecting to Redis...")
        await client.connect()
        
        if not client._available:
            print("❌ Redis connection failed!")
            print("   Check your REDIS_URL in .env file")
            return False
        
        print(f"✅ Connected to Redis: {client.redis_url.split('@')[-1]}\n")
        
        # Test SET operation
        print("2️⃣  Testing SET operation...")
        test_key = "test:connection"
        test_value = {"message": "Hello from NeedleAI!", "test": True}
        
        success = await client.set(test_key, test_value, expire=60)
        if success:
            print(f"✅ SET successful: {test_key}")
        else:
            print(f"❌ SET failed")
            return False
        
        # Test GET operation
        print("\n3️⃣  Testing GET operation...")
        retrieved = await client.get(test_key)
        if retrieved == test_value:
            print(f"✅ GET successful: {retrieved}")
        else:
            print(f"❌ GET failed: expected {test_value}, got {retrieved}")
            return False
        
        # Test EXISTS operation
        print("\n4️⃣  Testing EXISTS operation...")
        exists = await client.exists(test_key)
        if exists:
            print(f"✅ EXISTS successful: key found")
        else:
            print(f"❌ EXISTS failed: key not found")
            return False
        
        # Test DELETE operation
        print("\n5️⃣  Testing DELETE operation...")
        deleted = await client.delete(test_key)
        if deleted:
            print(f"✅ DELETE successful")
        else:
            print(f"❌ DELETE failed")
            return False
        
        # Test HASH operations
        print("\n6️⃣  Testing HASH operations...")
        hash_key = "test:hash"
        hash_data = {
            "user_id": "user_123",
            "name": "Test User",
            "credits": 100
        }
        
        await client.set_hash(hash_key, hash_data)
        retrieved_hash = await client.get_hash(hash_key)
        
        if retrieved_hash == hash_data:
            print(f"✅ HASH operations successful")
            await client.delete(hash_key)
        else:
            print(f"❌ HASH operations failed")
            return False
        
        # Test SESSION operations
        print("\n7️⃣  Testing SESSION operations...")
        session_id = "session_test_123"
        session_data = {
            "user_id": "user_456",
            "context": {"last_query": "test query"},
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        await client.store_session(session_id, session_data, expire=300)
        retrieved_session = await client.get_session(session_id)
        
        if retrieved_session == session_data:
            print(f"✅ SESSION operations successful")
            await client.delete_session(session_id)
        else:
            print(f"❌ SESSION operations failed")
            return False
        
        # Test INCREMENT operation
        print("\n8️⃣  Testing INCREMENT operation...")
        counter_key = "test:counter"
        count1 = await client.increment(counter_key)
        count2 = await client.increment(counter_key)
        count3 = await client.increment(counter_key, amount=5)
        
        if count1 == 1 and count2 == 2 and count3 == 7:
            print(f"✅ INCREMENT successful: 1 → 2 → 7")
            await client.delete(counter_key)
        else:
            print(f"❌ INCREMENT failed: {count1}, {count2}, {count3}")
            return False
        
        # Test HEALTH CHECK
        print("\n9️⃣  Testing HEALTH CHECK...")
        healthy = await client.health_check()
        if healthy:
            print(f"✅ Health check passed")
        else:
            print(f"❌ Health check failed")
            return False
        
        # Disconnect
        print("\n🔌 Disconnecting...")
        await client.disconnect()
        print("✅ Disconnected successfully")
        
        # Summary
        print("\n" + "="*50)
        print("✅ All Redis tests passed successfully!")
        print("="*50)
        print("\n🎯 Redis is ready for:")
        print("   • Session storage")
        print("   • Response caching")
        print("   • Rate limiting")
        print("   • Celery task queue")
        print("   • Real-time pub/sub")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await client.disconnect()
        except:
            pass


async def main():
    """Main entry point."""
    print("\n" + "="*50)
    print("🚀 NeedleAI Redis Connection Test")
    print("="*50 + "\n")
    
    success = await test_redis_connection()
    
    if success:
        print("\n✨ Redis setup is complete and working!\n")
        return 0
    else:
        print("\n⚠️  Redis setup needs attention. Check REDIS_SETUP.md\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


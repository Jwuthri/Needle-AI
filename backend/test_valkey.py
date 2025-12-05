#!/usr/bin/env python3
"""Test Valkey connection."""

import asyncio
from app.core.config.settings import get_settings
from app.services.redis_client import ValkeyClient


async def main():
    settings = get_settings()
    print(f"Testing Valkey connection to: {settings.redis_url.split('@')[-1]}")
    
    client = ValkeyClient()
    
    try:
        await client.connect()
        print("✓ Connected successfully")
        
        # Test set/get
        test_key = "test:valkey:key"
        test_value = "hello world"
        
        await client.set(test_key, test_value)
        print(f"✓ Set key: {test_key}")
        
        result = await client.get(test_key)
        print(f"✓ Got value: {result}")
        
        if result == test_value:
            print("✓ Value matches!")
        else:
            print(f"✗ Value mismatch: expected {test_value}, got {result}")
        
        # Cleanup
        await client.delete(test_key)
        print(f"✓ Deleted key: {test_key}")
        
        # Test health check
        is_healthy = await client.health_check()
        print(f"✓ Health check: {'passed' if is_healthy else 'failed'}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("✓ Disconnected")


if __name__ == "__main__":
    asyncio.run(main())


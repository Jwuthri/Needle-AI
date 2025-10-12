# Redis Setup Guide (Aiven/Valkey)

## ✅ Your Redis Configuration

### Connection Details

**Note**: This is an Aiven managed Valkey (Redis-compatible) instance with SSL/TLS encryption enabled.

## 🔧 Environment Configuration

### 1. Create .env file

```bash
cp env.template .env
```

### 2. Configure Redis in .env

Your `.env` file already has the correct Redis configuration:

```bash
# Redis Configuration (SSL Enabled)
REDIS_URL=
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=
```

## 🔐 SSL/TLS Configuration

The Redis client is automatically configured to handle SSL connections:

### Features
- ✅ **SSL Certificate Verification**: `ssl_cert_reqs=required`
- ✅ **Hostname Verification**: `ssl_check_hostname=True`
- ✅ **Automatic Detection**: Detects `rediss://` prefix
- ✅ **System CA Bundle**: Uses OS certificate store

### Code Implementation

```python
# app/services/redis_client.py
if self.redis_url.startswith("rediss://"):
    redis_config.update({
        "ssl_cert_reqs": "required",  # Require valid SSL certificate
        "ssl_check_hostname": True,    # Verify hostname matches certificate
    })
```

## 📦 Database Organization

Redis databases are used as follows:

| DB | Purpose | Configuration |
|----|---------|---------------|
| DB 0 | General caching & sessions | `REDIS_URL` |
| DB 0 | Celery broker (tasks queue) | `CELERY_BROKER_URL/0` |
| DB 1 | Celery results storage | `CELERY_RESULT_BACKEND/1` |
| DB 15 | Testing | `TEST_REDIS_URL` |

## 🧪 Testing Connection

### Test Redis Connection

```bash
python3 -c "
import asyncio
from app.services.redis_client import RedisClient

async def test():
    client = RedisClient()
    await client.connect()
    
    if client._available:
        print('✅ Redis connected successfully!')
        
        # Test operations
        await client.set('test_key', 'Hello Redis!')
        value = await client.get('test_key')
        print(f'✅ Test value: {value}')
        
        await client.delete('test_key')
        print('✅ All operations successful!')
    else:
        print('❌ Redis connection failed')
    
    await client.disconnect()

asyncio.run(test())
"
```

### Expected Output

```
Using SSL/TLS for Redis connection
Connected to Redis at valkey-needelai-needleai.b.aivencloud.com:28586
✅ Redis connected successfully!
✅ Test value: Hello Redis!
✅ All operations successful!
```

## 🚀 Starting Services

### 1. Start FastAPI (with Redis)

```bash
uvicorn app.main:app --reload
```

### 2. Start Celery Worker (uses Redis as broker)

```bash
celery -A app.core.celery_app worker --loglevel=info
```

### 3. Start Celery Beat (for scheduled tasks)

```bash
celery -A app.core.celery_app beat --loglevel=info
```

## 📊 Monitoring Redis

### Using redis-cli (via SSL tunnel)

```bash
# Install redis-cli if needed
brew install redis  # macOS
# or
sudo apt-get install redis-tools  # Linux

# Connect with SSL (note: requires stunnel or similar for SSL support)
redis-cli -h valkey-needelai-needleai.b.aivencloud.com -p 28586 --tls --cacert /path/to/ca.crt
```

### Using Python

```python
import asyncio
from app.services.redis_client import RedisClient

async def monitor():
    client = RedisClient()
    await client.connect()
    
    # Get all keys
    keys = await client.redis.keys('*')
    print(f"Total keys: {len(keys)}")
    
    # Get info
    info = await client.redis.info()
    print(f"Connected clients: {info['connected_clients']}")
    print(f"Used memory: {info['used_memory_human']}")
    
    await client.disconnect()

asyncio.run(monitor())
```

## 🎯 Use Cases

### 1. Session Storage

```python
from app.services.redis_client import RedisClient

client = RedisClient()
await client.connect()

# Store session
await client.store_session(
    session_id="session_123",
    session_data={"user_id": "user_456", "context": {...}},
    expire=86400  # 24 hours
)

# Retrieve session
session = await client.get_session("session_123")
```

### 2. Response Caching

```python
# Cache LLM response
await client.cache_response(
    cache_key="query_hash_abc",
    response={"answer": "...", "sources": [...]},
    expire=3600  # 1 hour
)

# Get cached response
cached = await client.get_cached_response("query_hash_abc")
```

### 3. Rate Limiting

```python
# Increment request count
count = await client.increment(f"rate_limit:user_{user_id}")

if count > 60:  # 60 requests per minute
    raise RateLimitExceeded()
```

### 4. Pub/Sub for Real-time Updates

```python
# Publisher
await client.publish("job_updates", {
    "job_id": "scraping_123",
    "status": "in_progress",
    "progress": 45
})

# Subscriber
pubsub = await client.subscribe(["job_updates"])
async for message in pubsub.listen():
    if message['type'] == 'message':
        data = json.loads(message['data'])
        print(f"Job {data['job_id']}: {data['progress']}%")
```

## 🔧 Troubleshooting

### Connection Timeout

```bash
# Check firewall rules
# Ensure port 28586 is accessible from your IP

# Test basic connectivity
telnet valkey-needelai-needleai.b.aivencloud.com 28586
```

### SSL Certificate Error

```python
# If certificate verification fails, check system CA bundle
import ssl
import certifi

print(f"CA bundle location: {certifi.where()}")
```

### Password Authentication Error

```bash
# Verify credentials in .env
echo $REDIS_URL

# Should output:
# rediss://default:AVNS_MlH2JatRMypE9-uiDF0@valkey-needelai-needleai.b.aivencloud.com:28586
```

### Memory Issues

```python
# Check Redis memory usage
info = await client.redis.info('memory')
print(f"Used memory: {info['used_memory_human']}")
print(f"Max memory: {info['maxmemory_human']}")
```

## 🔒 Security Best Practices

1. **Never commit .env** - It's already in `.gitignore`
2. **Rotate passwords regularly** - Update in Aiven console and .env
3. **Use SSL always** - `rediss://` not `redis://`
4. **Limit access** - Configure IP allowlist in Aiven
5. **Monitor access logs** - Check Aiven dashboard

## 📚 Additional Resources

- **Aiven Redis Documentation**: https://docs.aiven.io/docs/products/redis
- **Redis Python Client**: https://redis-py.readthedocs.io/
- **Celery with Redis**: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html

---

## ✅ Quick Checklist

- [x] Redis connection info added to `env.template`
- [x] SSL/TLS support enabled in Redis client
- [x] Celery configured to use Redis
- [x] Environment variables documented
- [x] Testing instructions provided
- [x] Security best practices listed

**Your Redis is ready to use! 🚀**


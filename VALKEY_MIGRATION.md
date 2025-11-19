# Redis to Valkey Migration

## Overview

The application has been migrated from Redis to Valkey. Valkey is a Redis-compatible, high-performance key-value store and is a direct drop-in replacement for Redis.

## What Changed

### 1. **Dependencies**
- Replaced `redis` and `aioredis` packages with `valkey>=6.1.1`
- Removed `opentelemetry-instrumentation-redis` (not needed for Valkey)

### 2. **Client Implementation**
- `RedisClient` has been replaced with `ValkeyClient`
- `RedisClient` now serves as a backward compatibility alias
- All internal references now use `valkey` library

### 3. **Configuration**
- Default URLs now use `valkeys://` protocol instead of `redis://`
- Settings support both `redis://`, `rediss://`, `valkey://`, and `valkeys://` protocols
- Environment variables remain the same (`REDIS_URL`, etc.) for backward compatibility

### 4. **Celery Integration**
- Celery broker and backend now use Valkey
- Automatic protocol conversion: `valkeys://` → `rediss://` for Celery compatibility
- SSL configuration is automatically added when using `valkeys://` protocol

## Migration Steps

### Update Environment Variables

Update your `.env` file to use the `valkeys://` protocol:

```bash
# Old Redis URL
REDIS_URL=rediss://default:password@host:port/0

# New Valkey URL
REDIS_URL=valkeys://default:password@host:port/0

# Celery URLs
CELERY_BROKER_URL=valkeys://default:password@host:port/0
CELERY_RESULT_BACKEND=valkeys://default:password@host:port/0
```

### Install Dependencies

```bash
cd backend
uv pip install -e .
```

### Test Connection

Run the test script to verify Valkey connectivity:

```bash
cd backend
python test_valkey.py
```

Expected output:
```
Testing Valkey connection to: host:port/0
✓ Connected successfully
✓ Set key: test:valkey:key
✓ Got value: hello world
✓ Value matches!
✓ Deleted key: test:valkey:key
✓ Health check: passed
✓ Disconnected
```

## Backward Compatibility

The migration maintains full backward compatibility:

1. **Imports**: All existing imports of `RedisClient` continue to work via alias
2. **Settings**: The `redis_url` setting name is preserved
3. **Methods**: All client methods remain the same
4. **Protocols**: Both `redis://` and `valkeys://` protocols are supported
5. **Celery**: Automatically converts `valkeys://` to `rediss://` (Celery doesn't support valkeys protocol)

## Key Files Modified

- `backend/app/services/redis_client.py` - Main client implementation
- `backend/app/core/celery_app.py` - Celery configuration
- `backend/app/core/config/settings.py` - Configuration defaults and validation
- `backend/pyproject.toml` - Dependency updates

## Valkey Benefits

1. **100% Redis Compatible**: Drop-in replacement with same commands and protocols
2. **Better Performance**: Optimized for high-throughput scenarios
3. **Active Development**: Regular updates and improvements
4. **No License Concerns**: Open source with permissive licensing

## Troubleshooting

### Connection Issues

If you encounter connection issues:

1. Verify your `REDIS_URL` environment variable uses `valkeys://` protocol
2. Check that credentials and host are correct
3. Ensure Valkey service is running and accessible
4. Test with the provided `test_valkey.py` script

### SSL/TLS Issues

Valkey handles SSL/TLS automatically when using `valkeys://` protocol:
- No manual SSL configuration needed for direct Valkey client
- Certificate verification is handled by the client
- Works seamlessly with Aiven and other hosted providers

**Note**: Celery converts `valkeys://` to `rediss://` automatically since kombu (Celery's messaging library) doesn't support the valkeys protocol. SSL configuration is added automatically.

### Import Errors

If you see import errors:
```bash
# Reinstall dependencies
cd backend
uv pip install -e .
```

## Support

For issues or questions about the Valkey migration, please check:
- [Valkey Documentation](https://valkey.io/docs/)
- [Valkey Python Client](https://github.com/valkey-io/valkey-py)


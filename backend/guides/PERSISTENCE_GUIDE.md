# 🔄 Memory Persistence Guide

## 🎯 **TL;DR - What Survives Server Restarts**

| Memory Type | Survives Restart? | Configuration Required |
|-------------|------------------|------------------------|
| **Vector Databases** (Pinecone, Weaviate, Qdrant, ChromaDB) | ✅ **YES** | Just API keys |
| **Redis Memory** (with persistence) | ✅ **YES** | Redis persistence config |
| **Database Memory** (PostgreSQL) | ✅ **YES** | Database connection |
| **File Memory** | ✅ **YES** | Persistent volume/path |
| **In-Memory Only** | ❌ **NO** | Not recommended for production |

## 🛠️ **Quick Production Setup**

### **1. Redis Persistence (Recommended for most apps)**

```env
# .env
REDIS_URL=redis://localhost:6379/0
USE_AGNO_AGENTS=true
MEMORY_TYPE=redis

# Redis persistence settings (add to redis.conf)
save 900 1 300 10 60 10000    # RDB snapshots
appendonly yes                # AOF logging
appendfsync everysec          # Sync frequency
```

### **2. Vector Database Persistence (Best for AI apps)**

```env
# Pinecone (easiest)
VECTOR_DATABASE=pinecone
PINECONE_API_KEY=your-api-key
PINECONE_INDEX_NAME=your-index
PINECONE_ENVIRONMENT=us-east-1

# Agno will automatically use persistent storage
USE_AGNO_AGENTS=true
USE_AGNO_MEMORY=true
```

## 📊 **What Happens on Server Restart**

### ❌ **BEFORE (Custom Implementation)**
```
Server Restart → All conversation history LOST
Memory starts empty → Users lose context
```

### ✅ **AFTER (Agno + Persistence)**
```
Server Restart → Agno automatically loads from:
├── Vector DB: Long-term semantic memory ✅
├── Redis: Recent conversations ✅
├── Database: Full conversation history ✅
└── Files: Local persistent storage ✅

Users pick up exactly where they left off! 🎉
```

## 🏗️ **Persistence Strategies by Environment**

### **Development**
```python
# File-based (simple, version control friendly)
memory = await create_persistent_file_memory()
# Data stored in: /data/agno/ (mount this volume)
```

### **Production (Small)**
```python
# Redis + Vector DB hybrid
memory = await create_persistent_hybrid_memory()
# Recent chats in Redis + long-term in Pinecone
```

### **Production (Enterprise)**
```python
# PostgreSQL for compliance
memory = await create_persistent_database_memory()
# Full ACID compliance + backup/recovery
```

## 🔧 **Configuration Examples**

### **Docker Compose with Persistence**

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    environment:
      - USE_AGNO_AGENTS=true
      - VECTOR_DATABASE=pinecone
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - agno_data:/data/agno  # Persistent volume
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes  # Enable persistence
    volumes:
      - redis_data:/data  # Persistent Redis data

volumes:
  agno_data:    # Agno file storage
  redis_data:   # Redis persistence
```

### **Kubernetes with Persistent Volumes**

```yaml
# k8s-persistent-memory.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: agno-memory-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: your-app:latest
        env:
        - name: USE_AGNO_AGENTS
          value: "true"
        - name: VECTOR_DATABASE
          value: "pinecone"
        volumeMounts:
        - name: agno-storage
          mountPath: /data/agno
      volumes:
      - name: agno-storage
        persistentVolumeClaim:
          claimName: agno-memory-pvc
```

## 🔄 **Backup & Recovery**

### **Automatic Backups**
```python
# Agno handles backups automatically
agent = Agent(
    memory=HybridMemory(
        backup_enabled=True,
        backup_interval=3600,       # Hourly backups
        backup_retention="30d",     # Keep 30 days
        backup_location="s3://your-bucket/backups"
    )
)
```

### **Manual Backup**
```python
# Export conversation data
await agent.memory.export_backup("/backups/conversations-2024-01-15.json")

# Restore from backup
await agent.memory.import_backup("/backups/conversations-2024-01-15.json")
```

## 📈 **Monitoring Persistence**

### **Health Checks**
```python
# Check if memory is persistent
persistence_status = await agent.memory.get_persistence_status()

print(f"Backend: {persistence_status['backend']}")
print(f"Persistent: {persistence_status['is_persistent']}")
print(f"Last Backup: {persistence_status['last_backup']}")
print(f"Storage Used: {persistence_status['storage_size']}")
```

### **Metrics to Monitor**
- Memory storage size
- Backup success rate
- Recovery time
- Data retention compliance

## 🚨 **Common Persistence Issues & Solutions**

### **Issue: Memory Lost on Restart**
```bash
# Check if Agno is using persistent backend
grep -r "storage=" app/core/memory/

# Solution: Configure persistent storage
export USE_AGNO_AGENTS=true
export REDIS_URL=redis://localhost:6379/0
```

### **Issue: Redis Data Not Persisting**
```bash
# Check Redis persistence config
redis-cli CONFIG GET save
redis-cli CONFIG GET appendonly

# Solution: Enable Redis persistence
redis-cli CONFIG SET save "900 1 300 10 60 10000"
redis-cli CONFIG SET appendonly yes
```

### **Issue: Vector DB Connection Lost**
```bash
# Check API keys
echo $PINECONE_API_KEY
curl -H "Api-Key: $PINECONE_API_KEY" https://api.pinecone.io/databases

# Solution: Verify credentials and network
```

## ⚡ **Performance Considerations**

### **Memory vs. Persistence Trade-offs**
```python
# Fast but less persistent
memory = ChatMemory(max_messages=100)

# Slower but fully persistent
memory = ChatMemory(
    storage=PostgreSQLStorage(),
    max_messages=10000,
    auto_save_interval=10  # Save every 10 seconds
)

# Balanced approach (recommended)
memory = HybridMemory(
    chat_memory=ChatMemory(max_messages=500),    # Recent in memory
    vector_memory=VectorMemory(max_items=100000) # Long-term persistent
)
```

## 🎯 **Best Practices**

### ✅ **DO**
- Use vector databases for production (inherently persistent)
- Configure Redis persistence (`appendonly yes`)
- Mount persistent volumes in containers
- Monitor backup success rates
- Test disaster recovery procedures

### ❌ **DON'T**
- Use in-memory storage in production
- Forget to configure Redis persistence
- Skip backup testing
- Ignore storage monitoring
- Store secrets in memory configurations

## 🚀 **Migration from Non-Persistent to Persistent**

```python
# 1. Export existing data (if any)
existing_sessions = await old_memory.get_all_sessions()

# 2. Create new persistent memory
persistent_memory = await create_persistent_hybrid_memory()

# 3. Import existing data
for session in existing_sessions:
    await persistent_memory.import_session(session)

# 4. Update configuration
# USE_AGNO_AGENTS=true
# MEMORY_TYPE=hybrid

# 5. Deploy with persistent volumes
```

## 🎉 **Result: Bulletproof Memory**

With proper persistence configuration:

- ✅ **Server restarts**: No data loss
- ✅ **Deployments**: Conversations preserved
- ✅ **Scaling**: Memory persists across instances
- ✅ **Disaster recovery**: Automatic backups
- ✅ **Compliance**: Full audit trails
- ✅ **User experience**: Seamless conversations

**Your AI assistant remembers everything, forever!** 🧠✨

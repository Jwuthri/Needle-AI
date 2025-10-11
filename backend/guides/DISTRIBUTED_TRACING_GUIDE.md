# 🔍 Distributed Tracing Guide for NeedleAi

> **Production-ready distributed tracing with OpenTelemetry, Jaeger, and Zipkin**

## 🎯 **What You Just Got**

A **complete distributed tracing system** with:
- **OpenTelemetry** instrumentation for FastAPI, SQLAlchemy, Redis, HTTP clients
- **Multiple backends**: Jaeger, Zipkin, OTLP, Console
- **Custom tracing decorators** for business logic
- **Automatic request correlation** with trace/span IDs
- **Performance monitoring** and error tracking
- **Production-ready configuration** with Docker Compose

---

## 🚀 **Quick Start**

### **1. Enable Tracing**

```env
# .env
ENABLE_TRACING=true
TRACING_EXPORTER=jaeger
TRACING_SAMPLE_RATE=1.0
```

### **2. Start Tracing Infrastructure**

```bash
# Start Jaeger
docker-compose -f docker/docker-compose.tracing.yml up jaeger -d

# Or start all tracing services
docker-compose -f docker/docker-compose.tracing.yml up -d
```

### **3. Run Your Application**

```bash
uvicorn app.main:app --reload
```

### **4. View Traces**

- **Jaeger UI**: http://localhost:16686
- **Zipkin UI**: http://localhost:9411

---

## 🏗️ **Architecture Overview**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │ OpenTelemetry   │    │  Trace Backend  │
│                 │    │   Collector     │    │  (Jaeger/Zipkin)│
│ ┌─────────────┐ │    │                 │    │                 │
│ │   Traces    │ ├────┼─ gRPC/HTTP ──── ┼────┤   Storage &     │
│ │   Metrics   │ │    │                 │    │     Query       │
│ │   Logs      │ │    │                 │    │                 │
│ └─────────────┘ │    └─────────────────┘    └─────────────────┘
└─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Trace Propagation Flow                       │
├─────────────────────────────────────────────────────────────────┤
│ HTTP Request → Middleware → Business Logic → Database → External │
│      ↓              ↓             ↓            ↓          ↓     │
│  Trace ID      Span Context   Custom Spans   DB Spans   HTTP    │
│   Created       Propagated     + Events     Auto-instr  Spans   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 **Configuration Options**

### **Environment Variables**

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TRACING` | `false` | Enable/disable distributed tracing |
| `TRACING_EXPORTER` | `console` | Exporter type: `console`, `jaeger`, `zipkin`, `otlp` |
| `TRACING_SAMPLE_RATE` | `1.0` | Sampling rate (0.0 to 1.0) |
| `JAEGER_ENDPOINT` | `http://localhost:14268/api/traces` | Jaeger collector endpoint |
| `ZIPKIN_ENDPOINT` | `http://localhost:9411/api/v2/spans` | Zipkin collector endpoint |
| `OTLP_ENDPOINT` | `http://localhost:4317` | OTLP gRPC collector endpoint |

### **Exporters**

#### **Console Exporter** (Development)
```env
TRACING_EXPORTER=console
```
- Prints traces to console
- Great for local development and debugging

#### **Jaeger Exporter** (Recommended)
```env
TRACING_EXPORTER=jaeger
JAEGER_ENDPOINT=http://localhost:14268/api/traces
```
- Rich UI with service maps
- Advanced search and filtering
- Performance analytics

#### **Zipkin Exporter**
```env
TRACING_EXPORTER=zipkin
ZIPKIN_ENDPOINT=http://localhost:9411/api/v2/spans
```
- Simple, lightweight UI
- Good for basic tracing needs

#### **OTLP Exporter** (Production)
```env
TRACING_EXPORTER=otlp
OTLP_ENDPOINT=http://localhost:4317
```
- Vendor-neutral protocol
- Works with multiple backends
- Production scalability

---

## 🎨 **Usage Examples**

### **1. Automatic Instrumentation**

Works out of the box for:
- **FastAPI requests** (routes, middleware, exceptions)
- **SQLAlchemy queries** (database operations)
- **Redis commands** (caching, sessions)
- **HTTP client calls** (external APIs)

### **2. Custom Tracing with Decorators**

```python
from app.core.tracing import trace_async_function, trace_sync_function

@trace_async_function("user_creation", {"component": "user_service"})
async def create_user(user_data: dict) -> dict:
    """Automatically traced async function."""
    # Your business logic here
    return {"user_id": "12345", "email": user_data["email"]}

@trace_sync_function("data_processing", {"component": "analytics"})
def process_data(data: list) -> dict:
    """Automatically traced sync function."""
    return {"processed": len(data)}
```

### **3. Manual Tracing with Context Managers**

```python
from app.core.tracing import trace_operation, add_span_attributes, add_span_event

async def complex_operation():
    with trace_operation("business_flow", {"flow": "user_onboarding"}) as span:

        # Add custom attributes
        add_span_attributes({
            "user.email": "user@example.com",
            "operation.type": "onboarding"
        })

        # Add events for key milestones
        add_span_event("validation.started", {"fields": 5})

        # Your business logic
        result = await validate_user_data()

        add_span_event("validation.completed", {"success": True})

        return result
```

### **4. Database Operations Tracing**

```python
from app.middleware.tracing_middleware import DatabaseTracingMixin

class UserRepository(DatabaseTracingMixin):
    async def create_user(self, user_data: dict):
        # Add database-specific tracing
        self.trace_database_operation(
            operation="insert",
            table="users",
            user_email=user_data["email"]
        )

        # Your database logic
        return await self.db.execute(insert_query, user_data)
```

### **5. External API Calls Tracing**

```python
from app.middleware.tracing_middleware import ExternalServiceTracingMixin

class EmailService(ExternalServiceTracingMixin):
    async def send_email(self, recipient: str, subject: str):
        # Add external service tracing
        self.trace_external_call(
            service="email_service",
            endpoint="/api/v1/send",
            method="POST",
            recipient=recipient
        )

        # Your HTTP client logic
        response = await self.http_client.post("/send", json=email_data)
        return response
```

---

## 🔍 **Trace Analysis & Debugging**

### **Finding Traces**

#### **By Service**
1. Open Jaeger UI: http://localhost:16686
2. Select service: `needleai`
3. Choose operation or leave blank for all
4. Click "Find Traces"

#### **By Trace ID**
```python
# In your application logs, you'll see:
logger.info(f"Processing request with trace_id: {get_trace_id()}")

# Use this ID to find the exact trace in Jaeger
```

#### **By Tags/Attributes**
Search for:
- `user.email=user@example.com`
- `error=true`
- `http.status_code=500`
- `component=user_service`

### **Performance Analysis**

#### **Slow Requests**
1. In Jaeger, search with `duration>2s`
2. Look at the waterfall view
3. Identify the slowest spans
4. Check database queries and external calls

#### **Error Analysis**
1. Search with `error=true`
2. View exception stack traces in span details
3. Follow the trace to see error propagation
4. Check error events and attributes

### **Service Dependencies**
1. Go to "System Architecture" tab
2. View service dependency graph
3. Identify critical path bottlenecks
4. Analyze cross-service communication patterns

---

## 📊 **Monitoring & Alerting**

### **Key Metrics to Monitor**

```yaml
# Example Prometheus queries for tracing metrics

# Request duration P95
histogram_quantile(0.95, http_request_duration_seconds_bucket{job="fastapi"})

# Error rate
rate(traces_total{status="error"}[5m]) / rate(traces_total[5m])

# Database query latency
histogram_quantile(0.95, db_query_duration_seconds_bucket)

# External service success rate
rate(external_requests_total{status="success"}[5m]) / rate(external_requests_total[5m])
```

### **Alert Rules**

```yaml
# High error rate
- alert: HighErrorRate
  expr: rate(traces_total{status="error"}[5m]) > 0.1
  for: 2m
  annotations:
    summary: "High error rate detected"

# Slow database queries
- alert: SlowDatabaseQueries
  expr: histogram_quantile(0.95, db_query_duration_seconds_bucket) > 1.0
  for: 5m
  annotations:
    summary: "Database queries are running slowly"
```

---

## 🚀 **Production Deployment**

### **1. Performance Considerations**

```python
# Optimize sampling for production
TRACING_SAMPLE_RATE=0.1  # Sample 10% of requests

# Use batching to reduce overhead
OTEL_BSP_MAX_EXPORT_BATCH_SIZE=1024
OTEL_BSP_EXPORT_TIMEOUT=5000
```

### **2. Security**

```yaml
# Sanitize sensitive data in traces
processors:
  transform:
    trace_statements:
      - context: span
        statements:
          # Remove sensitive attributes
          - delete_key(attributes, "user.password")
          - delete_key(attributes, "auth.token")
```

### **3. Scalable Architecture**

```yaml
# Use OTLP collector for production
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    command: ["--config=/etc/collector-config.yml"]
    # Configure multiple exporters, load balancing, etc.
```

### **4. Storage Optimization**

```bash
# Jaeger with Elasticsearch backend
SPAN_STORAGE_TYPE=elasticsearch
ES_SERVER_URLS=http://elasticsearch:9200

# Set retention policies
ES_INDEX_CLEANER_ENABLED=true
ES_INDEX_CLEANER_NUM_DAYS=7
```

---

## 🔧 **Troubleshooting**

### **Common Issues**

#### **No traces appearing**
```bash
# Check if tracing is enabled
echo $ENABLE_TRACING

# Verify collector is running
docker ps | grep jaeger

# Check application logs
docker logs your-app-container | grep -i tracing
```

#### **High overhead**
```python
# Reduce sampling rate
TRACING_SAMPLE_RATE=0.01

# Disable auto-instrumentation for specific components
OTEL_PYTHON_DISABLED_INSTRUMENTATIONS=urllib3,requests
```

#### **Missing spans**
```python
# Ensure proper context propagation
from opentelemetry.trace import set_span_in_context
from opentelemetry.context import attach

# When crossing async boundaries
ctx = set_span_in_context(span)
token = attach(ctx)
try:
    await some_async_operation()
finally:
    detach(token)
```

### **Debug Mode**

```env
# Enable debug logging
OTEL_LOG_LEVEL=debug
OTEL_PYTHON_LOG_CORRELATION=true

# Console exporter for debugging
TRACING_EXPORTER=console
```

---

## 📚 **Advanced Features**

### **Custom Span Processors**

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanProcessor

class CustomSpanProcessor(SpanProcessor):
    def on_start(self, span, parent_context):
        # Add custom logic on span start
        pass

    def on_end(self, span):
        # Add custom logic on span end (e.g., metrics)
        pass

# Add to tracer provider
tracer_provider.add_span_processor(CustomSpanProcessor())
```

### **Context Propagation**

```python
# Propagate trace context to background tasks
from opentelemetry import context

current_context = context.get_current()

# In background task
with context.attach(current_context):
    # Spans created here will be part of the original trace
    await background_operation()
```

### **Custom Metrics with Traces**

```python
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader

# Create metrics that correlate with traces
request_counter = meter.create_counter(
    "requests_total",
    description="Total number of requests",
)

# In traced function
request_counter.add(1, {"trace_id": get_trace_id()})
```

---

## 🎯 **Next Steps**

1. **Start with Console**: Enable `TRACING_EXPORTER=console` for local development
2. **Add Custom Traces**: Use decorators for key business operations
3. **Deploy Jaeger**: Set up `docker-compose.tracing.yml` for team development
4. **Monitor Performance**: Set up alerts for key metrics
5. **Scale for Production**: Implement OTLP collector with proper storage

---

## 📖 **Resources**

- **OpenTelemetry Python**: https://opentelemetry.io/docs/python/
- **Jaeger Documentation**: https://www.jaegertracing.io/docs/
- **Zipkin Documentation**: https://zipkin.io/pages/quickstart
- **OTLP Specification**: https://opentelemetry.io/docs/specs/otlp/

---

**🎉 You now have enterprise-grade distributed tracing!** Start with console exporter, add custom traces to key operations, then deploy Jaeger for the full experience.

# Needle AI

> 🚀 **AI-Powered Product Gap Analysis Platform** built with **FastAPI** + **Next.js** + **Agno** + **OpenRouter**

Needle AI uses advanced LLM analysis to identify product gaps across entire markets by aggregating and analyzing customer feedback from app stores, e-commerce reviews, Reddit discussions, support tickets, and more. Discover actionable insights on what customers desperately need but can't find anywhere.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a393?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black?style=flat&logo=next.js)](https://nextjs.org)
[![Agno](https://img.shields.io/badge/Agno-2.0+-blue?style=flat)](https://docs.agno.com)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-500%2B%20models-green?style=flat)](https://openrouter.ai)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178c6?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ed?style=flat&logo=docker)](https://www.docker.com)

---

## ✨ **Key Features**

### 🔍 **Multi-Source Gap Analysis**
- **📱 App Store Reviews**: Google Play & Apple App Store scraping and analysis
- **🛍️ E-commerce Reviews**: Amazon and other marketplace feedback aggregation
- **💬 Reddit Analysis**: Discussion mining via Apify for real user pain points
- **🎫 Support Tickets**: Import and analyze support data
- **🌐 Forum Discussions**: Cross-platform feedback collection
- **📊 Custom Data Upload**: CSV/JSON upload for proprietary feedback

### 🧠 **AI-Powered Intelligence**
- **500+ Models** via [OpenRouter](https://openrouter.ai) (GPT-5, Claude 3.7, Gemini 2.5 Pro, etc.)
- **Smart Gap Detection**: LLM identifies patterns and unmet needs across thousands of data points
- **Smart Clustering**: Groups similar complaints into actionable product opportunities
- **Competitor Gap Analysis**: See what features competitors are missing
- **Trend Detection**: Track how gaps evolve over time
- **Semantic Search**: Find specific pain points across all feedback sources

### 📈 **Actionable Insights**
- **Gap Scoring**: Priority ranking based on frequency and sentiment
- **Evidence-Based Reports**: PDF/Markdown reports with source citations
- **Opportunity Sizing**: Market demand estimation for each gap
- **Export & Share**: Multiple format support for team collaboration
- **Real-Time Processing**: Upload data and get insights in minutes

### 🚀 **Production-Ready Architecture**
- **FastAPI Backend** with async/await support
- **Next.js Frontend** with modern UI and data visualization
- **Vector Database** (Pinecone/Qdrant) for semantic analysis
- **Background Task Processing** with Celery workers
- **Docker Compose** setup for easy deployment
- **Scalable Infrastructure** with Redis, PostgreSQL, and microservices support

---

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │────│   FastAPI       │────│   Agno Agent    │
│   Frontend      │    │   Backend       │    │   Framework     │
│                 │    │                 │    │                 │
│ • TypeScript    │    │ • Python 3.11+ │    │ • OpenRouter    │
│ • Tailwind CSS  │    │ • Async/Await   │    │ • 500+ Models   │
│ • WebSocket     │    │ • Pydantic      │    │ • Memory        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
    ┌────────────────────────────┴────────────────────────────┐
    │                                                         │
┌───▼────┐ ┌────────┐ ┌────────┐ ┌─────────────┐ ┌──────────┐
│ Redis  │ │ Kafka  │ │RabbitMQ│ │Pinecone Vector│ │PostgreSQL│
│ Cache  │ │Streams │ │ Queue  │ │  Database   │ │ Database │
└────────┘ └────────┘ └────────┘ └─────────────┘ └──────────┘
```

---

## 🚀 **Quick Start**

### 1. **Prerequisites**
```bash
# Install uv (ultra-fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Node.js 18+
# https://nodejs.org/

# Install Docker & Docker Compose
# https://docs.docker.com/get-docker/
```

### 2. **Environment Setup**
```bash
# Copy environment files
cp backend/.env.template backend/.env
cp frontend/.env.template frontend/.env

# Set your API keys in backend/.env:
# - ANTHROPIC_API_KEY or OPENAI_API_KEY (for LLM analysis)
# - APIFY_API_TOKEN (for web scraping)
# - PINECONE_API_KEY (for semantic search)
# - DATABASE_URL (PostgreSQL connection)
```

### 3. **Start with Docker Compose** ⚡
```bash
# Start all services (recommended for first run)
docker-compose up -d

# Or use the development setup
docker-compose -f docker-compose.dev.yml up -d
```

### 4. **Manual Development Setup** 🛠️
```bash
# Backend
cd backend
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e .
uv pip list
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

### 5. **Access Your Gap Analysis Platform** 🎉
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

---

## 🎯 **Use Cases**

### **Product Managers**
- Identify feature gaps in your product category
- Validate product ideas with real customer pain points
- Prioritize roadmap based on actual market needs

### **Entrepreneurs**
- Discover untapped market opportunities
- Find gaps competitors aren't solving
- Validate startup ideas before building

### **Market Researchers**
- Analyze entire product categories at scale
- Track sentiment trends over time
- Generate comprehensive market reports

### **UX Researchers**
- Aggregate user feedback from multiple sources
- Identify common usability complaints
- Find patterns in user needs

---

## 🤖 **LLM Configuration**

### **Supported Models**
Choose from 500+ models for gap analysis:

```python
# Recommended for gap analysis
"anthropic/claude-3.5-sonnet"    # Best for reasoning & analysis
"openai/gpt-4o"                  # Reliable and accurate
"google/gemini-1.5-pro"          # Excellent for large contexts

# Latest models
"gpt-5"                          # OpenAI's latest
"anthropic/claude-3.7-sonnet"    # Enhanced capabilities
"google/gemini-2.5-pro"          # Google's flagship

# Cost-effective options
"openai/gpt-4o-mini"             # Fast and affordable
"anthropic/claude-3-haiku"       # Speed optimized
```

### **Analysis Configuration**
- **Semantic Clustering**: Vector embeddings for grouping similar feedback
- **Sentiment Analysis**: Gauge urgency and frustration levels
- **Trend Detection**: Time-series analysis of emerging gaps
- **Multi-Language**: Support for international feedback sources

---

## 📚 **API Endpoints**

### **Gap Analysis**
```bash
# Create new analysis
POST /api/v1/analysis
{
  "category": "meal planning apps",
  "sources": ["reddit", "google_play", "app_store"],
  "max_items": 500
}

# Get analysis results
GET /api/v1/analysis/{analysis_id}

# List all analyses
GET /api/v1/analysis

# Get top gaps from analysis
GET /api/v1/analysis/{analysis_id}/gaps
```

### **Data Collection**
```bash
# Upload custom feedback data
POST /api/v1/data/upload
{
  "file": <file>,
  "source_type": "csv"
}

# Trigger Reddit scraping
POST /api/v1/scraping/reddit
{
  "subreddits": ["productmanagement", "saas"],
  "keywords": ["need", "missing", "frustrating"]
}

# Scrape app store reviews
POST /api/v1/scraping/app-store
{
  "app_id": "com.example.app",
  "max_reviews": 1000
}
```

### **Reports & Insights**
```bash
# Generate report
POST /api/v1/reports/{analysis_id}/generate
{
  "format": "pdf"  # or "markdown"
}

# Get gap trends over time
GET /api/v1/analysis/{analysis_id}/trends

# Search across all feedback
POST /api/v1/search
{
  "query": "payment integration issues",
  "analysis_id": "uuid-here"
}
```

### **Background Tasks**
```bash
# Trigger asynchronous LLM completion
POST /api/v1/tasks/llm/completion
{
  "prompt": "Explain quantum computing",
  "model": "gpt-4",
  "delay_seconds": 10
}

# Process chat message asynchronously
POST /api/v1/tasks/chat/process
{
  "message": "Hello",
  "session_id": "uuid-here"
}

# Get task status
GET /api/v1/tasks/{task_id}

# List all active tasks
GET /api/v1/tasks

# Trigger system health check
POST /api/v1/tasks/system/health-check

# Send notification
POST /api/v1/tasks/notifications
{
  "recipient": "user@example.com",
  "message": "Task completed",
  "notification_type": "success"
}
```

---

## 🔧 **Configuration**

### **Backend Settings** (`backend/.env`)
```bash
# LLM Configuration
OPENROUTER_API_KEY=your_key_here
DEFAULT_MODEL=anthropic/claude-4.5-sonnet

# Web Scraping
APIFY_API_TOKEN=your_apify_token

# Vector Database for Semantic Search
VECTOR_DATABASE=pinecone
PINECONE_API_KEY=your_pinecone_key
PINECONE_ENVIRONMENT=gcp-starter

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/needleai

# Redis for Caching & Tasks
REDIS_URL=redis://localhost:6379/0

# Celery Background Tasks
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_TASK_ALWAYS_EAGER=false  # Set to true for testing

# Application
ENVIRONMENT=development
SECRET_KEY=your-secret-key-change-in-production
```

### **Frontend Settings** (`frontend/.env.local`)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000

```

---

## 🚢 **Deployment**

### **Using Docker** (Recommended)
```bash
# Production build
docker-compose -f docker-compose.prod.yml up -d

# Or use the deployment script
./backend/scripts/deploy.sh
```

### **Manual Deployment**
```bash
# Backend
cd backend
uv pip install -e .
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# Start Celery workers (in separate terminals)
celery -A app.core.celery_app:celery_app worker --queues=general --concurrency=2
celery -A app.core.celery_app:celery_app worker --queues=chat --concurrency=3
celery -A app.core.celery_app:celery_app worker --queues=llm --concurrency=2

# Optional: Start Celery Flower for monitoring
celery -A app.core.celery_app:celery_app flower --port=5555

# Frontend
cd frontend
npm run build
npm start
```

### **Environment Variables for Production**
- Set `ENVIRONMENT=production`
- Use strong `SECRET_KEY`
- Configure proper `CORS_ORIGINS`
- Set up SSL/TLS certificates
- Use managed database services

- Configure pinecone production instance


---

## 📁 **Project Structure**

```
needleai/
├── 📁 backend/                 # FastAPI Backend
│   ├── 📁 app/
│   │   ├── 📁 api/v1/         # API routes
│   │   ├── 📁 core/           # Core business logic
│   │   │   ├── 📁 llm/        # Agno + OpenRouter integration
│   │   │   ├── 📁 memory/     # Vector & Redis memory
│   │   │   └── 📁 security/   # Auth & rate limiting
│   │   ├── 📁 models/         # Pydantic models
│   │   ├── 📁 services/       # Business services
│   │   ├── 📁 tasks/          # Celery background tasks
│   │   └── 📁 utils/          # Utilities
│   ├── 📁 docker/             # Docker configurations
│   ├── 📁 scripts/            # Deployment scripts
│   └── 📄 pyproject.toml      # Python dependencies (uv)
│
├── 📁 frontend/               # Next.js Frontend
│   ├── 📁 src/
│   │   ├── 📁 app/            # Next.js App Router
│   │   ├── 📁 components/     # React components
│   │   │   ├── 📁 ui/         # Base UI components
│   │   │   └── 📁 chat/       # Chat interface
│   │   ├── 📁 hooks/          # Custom React hooks
│   │   ├── 📁 lib/            # Utilities & API client
│   │   └── 📁 types/          # TypeScript definitions
│   └── 📄 package.json       # Node.js dependencies
│
├── 📄 docker-compose.yml     # Development services
├── 📄 docker-compose.prod.yml # Production setup
└── 📄 README.md              # This file
```

---

## 🧪 **Development**

### **Running Tests**
```bash
# Backend tests
cd backend
uv run pytest

# Frontend tests
cd frontend
npm test
```

### **Code Quality**
```bash
# Backend linting & formatting
cd backend
uv run black .
uv run isort .
uv run ruff check .
uv run mypy .

# Frontend linting
cd frontend
npm run lint
npm run type-check
```

### **Database Migrations**

```bash
cd backend
uv run alembic revision --autogenerate -m "Description"
uv run alembic upgrade head
```


---

## 🔍 **Monitoring & Health Checks**

- **Health Check**: `GET /health`
- **Metrics**: `GET /metrics` (Prometheus format)
- **Agent Status**: `GET /api/v1/agent/status`

- **Vector DB Health**: `GET /api/v1/memory/health`


---

## 🤝 **Contributing**

### 🔧 **Setup Pre-commit Hooks**

We use pre-commit hooks to ensure code quality. Set them up before making changes:

```bash
# Install and setup pre-commit hooks
./scripts/setup-pre-commit.sh

# Or manually:
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The hooks will automatically check:
- **Python**: Black formatting, autoflake unused import removal, isort import sorting, flake8 linting, mypy type checking
- **Frontend**: Prettier formatting, ESLint linting
- **Security**: Secret detection, private key scanning
- **General**: Trailing whitespace, file endings, YAML/JSON validation

### 🚀 **Contribution Steps**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. **Setup pre-commit hooks**: `./scripts/setup-pre-commit.sh`
4. Make your changes
5. Run tests: `uv run pytest && npm test`
6. Commit: `git commit -m 'Add amazing feature'` (pre-commit hooks will run automatically)
7. Push: `git push origin feature/amazing-feature`
8. Open a Pull Request

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- **[Anthropic Claude](https://anthropic.com)** / **[OpenAI](https://openai.com)** - Advanced LLM analysis
- **[Apify](https://apify.com)** - Web scraping platform for Reddit, reviews, etc.
- **[FastAPI](https://fastapi.tiangolo.com)** - Modern Python web framework
- **[Next.js](https://nextjs.org)** - React framework for production
- **[Pinecone](https://pinecone.io)** - Vector database for semantic search
- **[shadcn/ui](https://ui.shadcn.com)** - Beautiful UI components
- **[OpenRouter](https://openrouter.ai)** - Unified access to 500+ AI models


---

## 📞 **Support**

- 📧 **Email**: julien.wut@gmail.com
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/needleai/issues)
- 💡 **Feature Requests**: [Request a Feature](https://github.com/yourusername/needleai/issues/new)
- 📖 **Documentation**: [Project Wiki](https://github.com/yourusername/needleai/wiki)

---

<div align="center">

**Built with ❤️ by the Needle AI team**

**Uncover what customers need — before your competitors do**

[⚡ FastAPI](https://fastapi.tiangolo.com) • [⚛️ Next.js](https://nextjs.org) • [🤖 Claude/GPT](https://anthropic.com) • [🕷️ Apify](https://apify.com)

⭐ **Star us on GitHub — it helps!**

</div>

# Production Deployment Guide

## Architecture Summary
The system is designed as a microservices architecture:
1. **API Gateway**: handled by FastAPI.
2. **Task Queue**: Celery (integrated for long-running research tasks).
3. **Data Layer**: PostgreSQL for structured data, Redis for caching/memory.
4. **Vector Layer**: FAISS (local) or ChromaDB (containerized).

## Deployment Steps

### 1. Environment Configuration
Create a `.env` file in the root directory:
```env
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@db:5432/ai_researcher
REDIS_HOST=redis
TAVILY_API_KEY=your_key
OPENAI_API_KEY=your_key
SECRET_KEY=your_super_secret_key
```

### 2. Docker Swarm / Kubernetes
The provided `docker-compose.yml` is compatible with Docker Swarm. For Kubernetes, use the included Helm charts (placeholder logic):
```bash
kubectl apply -f k8s/
```

### 3. CI/CD Pipeline
Recommended pipeline:
- **Linting**: flake8 (python), eslint (react).
- **Testing**: pytest, vitest.
- **Build**: Multi-stage Docker builds.
- **Deploy**: AWS ECS, GKE, or Azure Kubernetes Service.

## Security Hardening
- **SSL/TLS**: Use Nginx as a reverse proxy with Let's Encrypt.
- **Rate Limiting**: Configured in FastAPI via Redis.
- **Auth**: JWT tokens with 1-hour expiration and refresh logic.

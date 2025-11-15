# Deployment Guide - US Financial Statement Database

This guide provides step-by-step instructions for deploying the US Financial Statement Database on various platforms.

## Table of Contents

- [Replit Deployment (Recommended)](#replit-deployment)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)

---

## Replit Deployment (Recommended)

The project is optimized for Replit with automatic setup.

### Prerequisites

- Replit account
- GitHub repository with this code

### Steps

1. **Import to Replit**
   - Go to [Replit](https://replit.com)
   - Click "Create Repl"
   - Choose "Import from GitHub"
   - Paste repository URL
   - Click "Import from GitHub"

2. **Configure Database**
   - In Replit sidebar, click "Database" icon
   - Enable PostgreSQL database
   - Copy the connection string

3. **Set Environment Variables**

   In the Replit "Secrets" tab (Tools → Secrets), add:

   ```env
   DATABASE_URL=<your-postgres-url-from-replit>
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=<generate-with-openssl-rand-hex-32>
   VALID_API_KEYS=demo-key-12345,prod-key-67890
   SEC_USER_AGENT=YourCompany contact@yourcompany.com
   API_HOST=0.0.0.0
   API_PORT=8000
   ENVIRONMENT=production
   DEBUG=false
   ```

4. **Start the Application**
   - Click the "Run" button
   - The `start.sh` script will:
     - Install dependencies
     - Run database migrations
     - Start Redis
     - Start Celery workers
     - Start FastAPI server

5. **Access Your Application**
   - API Documentation: `https://<your-repl>.replit.dev/docs`
   - Web Interface: `https://<your-repl>.replit.dev/`
   - Health Check: `https://<your-repl>.replit.dev/health`

6. **Initialize with Sample Data**

   Open the Replit Shell and run:
   ```bash
   cd backend
   python scripts/init_db.py
   ```

7. **Start Backfilling Data**
   ```bash
   cd backend
   python scripts/backfill.py --ticker AAPL --years 10
   ```

### Replit-Specific Configuration

The project includes:
- `.replit` - Replit configuration
- `replit.nix` - Nix packages (Python, PostgreSQL, Redis)
- `start.sh` - Startup script

### Troubleshooting Replit

**Issue: Database connection fails**
- Ensure PostgreSQL is enabled in Replit
- Check `DATABASE_URL` in Secrets matches the Replit database URL

**Issue: Redis not starting**
```bash
# In Replit Shell
redis-server --daemonize yes
```

**Issue: Port already in use**
- Replit automatically handles port mapping
- Ensure `API_PORT=8000` in secrets

---

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Git

### Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd Public-Stocks-Database
   ```

2. **Set Up Python Environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install PostgreSQL**

   **macOS:**
   ```bash
   brew install postgresql@15
   brew services start postgresql@15
   createdb financial_db
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install postgresql-15
   sudo systemctl start postgresql
   sudo -u postgres createdb financial_db
   ```

4. **Install Redis**

   **macOS:**
   ```bash
   brew install redis
   brew services start redis
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

5. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

   Minimum `.env`:
   ```env
   DATABASE_URL=postgresql://localhost:5432/financial_db
   REDIS_URL=redis://localhost:6379/0
   SECRET_KEY=dev-secret-key-change-in-production
   VALID_API_KEYS=demo-key-12345
   SEC_USER_AGENT=Dev contact@localhost
   DEBUG=true
   ENVIRONMENT=development
   ```

6. **Initialize Database**
   ```bash
   cd backend
   python scripts/init_db.py
   alembic upgrade head
   ```

7. **Run Services**

   **Terminal 1 - API:**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

   **Terminal 2 - Celery Worker:**
   ```bash
   cd backend
   celery -A etl.tasks worker --loglevel=info
   ```

   **Terminal 3 - Celery Beat:**
   ```bash
   cd backend
   celery -A etl.tasks beat --loglevel=info
   ```

   **Terminal 4 - Frontend:**
   ```bash
   cd frontend/public
   python -m http.server 3000
   ```

8. **Verify Installation**
   - API: http://localhost:8000/docs
   - Frontend: http://localhost:3000
   - Health: http://localhost:8000/health

---

## Docker Deployment

### Prerequisites

- Docker 20+
- Docker Compose

### Docker Setup

1. **Create `docker-compose.yml`**
   ```yaml
   version: '3.8'

   services:
     postgres:
       image: postgres:15
       environment:
         POSTGRES_DB: financial_db
         POSTGRES_USER: financial_user
         POSTGRES_PASSWORD: changeme
       volumes:
         - postgres_data:/var/lib/postgresql/data
       ports:
         - "5432:5432"

     redis:
       image: redis:7
       ports:
         - "6379:6379"

     backend:
       build: ./backend
       command: uvicorn app.main:app --host 0.0.0.0 --port 8000
       environment:
         DATABASE_URL: postgresql://financial_user:changeme@postgres:5432/financial_db
         REDIS_URL: redis://redis:6379/0
         SECRET_KEY: change-in-production
         VALID_API_KEYS: demo-key-12345
       ports:
         - "8000:8000"
       depends_on:
         - postgres
         - redis

     celery_worker:
       build: ./backend
       command: celery -A etl.tasks worker --loglevel=info
       environment:
         DATABASE_URL: postgresql://financial_user:changeme@postgres:5432/financial_db
         REDIS_URL: redis://redis:6379/0
       depends_on:
         - postgres
         - redis

     celery_beat:
       build: ./backend
       command: celery -A etl.tasks beat --loglevel=info
       environment:
         DATABASE_URL: postgresql://financial_user:changeme@postgres:5432/financial_db
         REDIS_URL: redis://redis:6379/0
       depends_on:
         - postgres
         - redis

   volumes:
     postgres_data:
   ```

2. **Create `backend/Dockerfile`**
   ```dockerfile
   FROM python:3.11-slim

   WORKDIR /app

   RUN apt-get update && apt-get install -y \
       postgresql-client \
       && rm -rf /var/lib/apt/lists/*

   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   COPY . .

   EXPOSE 8000

   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Initialize Database**
   ```bash
   docker-compose exec backend python scripts/init_db.py
   ```

---

## Production Deployment

### Recommended Stack

- **Platform**: AWS, GCP, or Azure
- **App Server**: Multiple Gunicorn workers with Uvicorn
- **Database**: Managed PostgreSQL (RDS, Cloud SQL, etc.)
- **Cache/Queue**: Managed Redis (ElastiCache, etc.)
- **Load Balancer**: NGINX or cloud LB
- **SSL**: Let's Encrypt or cloud certificates

### Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Generate secure API keys
- [ ] Use managed PostgreSQL with backups
- [ ] Enable PostgreSQL connection pooling
- [ ] Use managed Redis with persistence
- [ ] Set up monitoring (Prometheus, DataDog, etc.)
- [ ] Configure logging (CloudWatch, Stackdriver, etc.)
- [ ] Set up error tracking (Sentry)
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Set rate limiting on API
- [ ] Schedule database backups
- [ ] Set up alerting for failures
- [ ] Document disaster recovery plan

### Environment Variables (Production)

```env
# Database
DATABASE_URL=postgresql://user:pass@db-host:5432/financial_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis-host:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Security
SECRET_KEY=<64-char-random-string>
VALID_API_KEYS=<secure-keys>
CORS_ORIGINS=https://yourdomain.com

# SEC EDGAR
SEC_USER_AGENT=YourCompany contact@yourcompany.com
SEC_RATE_LIMIT_DELAY=0.1

# Environment
ENVIRONMENT=production
DEBUG=false

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
```

### Scaling Considerations

**Vertical Scaling:**
- Start with 2 CPU, 4GB RAM
- Monitor CPU and memory usage
- Scale up as needed

**Horizontal Scaling:**
- Use load balancer for multiple API instances
- Scale Celery workers independently
- Use read replicas for database

**Database Optimization:**
- Enable query logging and analyze slow queries
- Add indexes based on usage patterns
- Consider partitioning `financial_data` table by year
- Regularly refresh materialized views

### Monitoring

**Key Metrics:**
- API response time (p50, p95, p99)
- Database query time
- Celery task queue length
- Error rate
- CPU and memory usage
- Database connections

**Health Checks:**
```python
# Already implemented at /health
GET /health
```

### Backup Strategy

**Database:**
```bash
# Daily backup
pg_dump financial_db > backup_$(date +%Y%m%d).sql

# Automated with cron
0 2 * * * pg_dump financial_db > /backups/backup_$(date +\%Y\%m\%d).sql
```

**Retention:**
- Keep daily backups for 7 days
- Keep weekly backups for 4 weeks
- Keep monthly backups for 12 months

---

## Post-Deployment

### Verify Deployment

1. **Health Check**
   ```bash
   curl https://your-domain.com/health
   ```

2. **API Documentation**
   ```
   https://your-domain.com/docs
   ```

3. **Test API Endpoint**
   ```bash
   curl -H "X-API-Key: your-key" \
     https://your-domain.com/api/v1/company/AAPL
   ```

### Initial Data Load

```bash
# Start with major companies
python scripts/backfill.py --file sp500.txt --years 10

# Monitor progress
celery -A etl.tasks flower  # Celery monitoring UI
```

### Monitoring Setup

- Set up application monitoring (Sentry, New Relic, etc.)
- Configure log aggregation (ELK stack, CloudWatch, etc.)
- Set up uptime monitoring (Pingdom, UptimeRobot, etc.)
- Create dashboards for key metrics

---

## Troubleshooting

### Common Issues

**Database connection pool exhausted:**
- Increase `DATABASE_POOL_SIZE`
- Check for connection leaks
- Enable connection pooling at app level

**Celery tasks not running:**
- Verify Redis is accessible
- Check Celery worker logs
- Ensure correct broker URL

**Slow API responses:**
- Check database query performance
- Enable query caching
- Add missing indexes
- Increase API workers

**SEC rate limiting:**
- Increase `SEC_RATE_LIMIT_DELAY`
- Implement exponential backoff
- Use SEC EDGAR API if available

---

## Support

For deployment issues:
- Check logs first
- Review documentation
- Open GitHub issue
- Contact support@example.com

---

**Last Updated:** 2024

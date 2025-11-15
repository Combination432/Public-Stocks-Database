#!/bin/bash

# Replit startup script for US Financial Statement Database

echo "Starting US Financial Statement Database..."

# Install Python dependencies if needed
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
else
    source backend/venv/bin/activate
fi

# Run database migrations
echo "Running database migrations..."
cd backend
alembic upgrade head
cd ..

# Start Redis (for Celery and caching)
redis-server --daemonize yes --dir /tmp

# Start Celery worker in background
echo "Starting Celery worker..."
cd backend
celery -A etl.tasks worker --loglevel=info --detach
cd ..

# Start Celery beat (scheduler) in background
echo "Starting Celery beat scheduler..."
cd backend
celery -A etl.tasks beat --loglevel=info --detach
cd ..

# Start FastAPI backend
echo "Starting FastAPI server on port 8000..."
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

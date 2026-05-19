FROM python:3.12-slim AS base

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app/ ./app/

EXPOSE 8000

# Run with gunicorn-style uvicorn worker for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

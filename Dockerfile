FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt1-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 8790

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8790", "--timeout", "120", "--access-logfile", "-", "src.app:app"]

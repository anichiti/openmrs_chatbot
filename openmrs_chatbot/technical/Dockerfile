FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories
RUN mkdir -p /app/vectorstore/chroma_data \
    && mkdir -p /app/knowledge_base/doctor \
    && mkdir -p /app/knowledge_base/patient \
    && mkdir -p /app/logs

# Expose port for future API service
EXPOSE 8000

# Default command
CMD ["python", "main.py"]

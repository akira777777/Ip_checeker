# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=app_optimized.py
ENV FLASK_HOST=0.0.0.0
ENV LOCAL_ONLY=false

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements_optimized.txt .
RUN pip install --no-cache-dir -r requirements_optimized.txt

# Copy project files
COPY . .

# Create cache directory
RUN mkdir -p /app/cache && chmod 777 /app/cache

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app_optimized.py"]

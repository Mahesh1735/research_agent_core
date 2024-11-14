# Use Python 3.10 slim image
FROM python:3.10-slim

# Install PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV PORT=8080

# Run the application
CMD exec gunicorn --bind :$PORT --workers 5 --threads 64 --timeout 0 api:app

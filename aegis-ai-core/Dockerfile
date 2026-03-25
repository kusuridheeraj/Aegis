FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Use 'uv' instead of 'pip' for 10x to 100x faster package installations
RUN pip install uv

COPY requirements.txt .

# Install dependencies using uv with a cache mount to drastically speed up rebuilds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
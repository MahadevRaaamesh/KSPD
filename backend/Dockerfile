FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for FAISS and compiled Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    libomp-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate the mock SQLite DB and FAISS index during the build
# so it is bundled in the container for AppSail deployment
RUN python scripts/generate_data.py
RUN python scripts/build_embeddings.py

# Expose port (Catalyst AppSail automatically assigns a port, usually 9000, 
# but FastAPI defaults to 8000. Catalyst will inject X_ZOHO_CATALYST_LISTEN_PORT)
EXPOSE 9000

# Run FastAPI using the port injected by Catalyst
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT:-9000}"]

FROM python:3.12-slim

WORKDIR /src

# --- C-LEVEL IO DEPENDENCIES ---
# libmagic1 is strictly required for binary MIME signature validation
RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*
# -------------------------------

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --timeout=1000 --retries=10 -r requirements.txt

# Copy source code
COPY backend/ /src/backend/
COPY ingestion/ /src/ingestion/
COPY scripts/ /src/scripts/

# Set PYTHONPATH
ENV PYTHONPATH=/src/backend:/src
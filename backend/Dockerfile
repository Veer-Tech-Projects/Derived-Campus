FROM python:3.12-slim

WORKDIR /src

# --- C-LEVEL IO DEPENDENCIES ---
# libmagic1 is strictly required for binary MIME signature validation
# curl is strictly required for build-time static dataset injection
RUN apt-get update && apt-get install -y \
    libmagic1 \
    curl \
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

# --- STATIC DATASET INJECTION (Phase 2 Location Pipeline) ---
# Fetches the PIN code dataset during build to prevent Git bloat
RUN mkdir -p /src/ingestion/assets && \
    curl -sSL https://raw.githubusercontent.com/sahilshekhawat/Pincodes-India/master/pincodes.json -o /src/ingestion/assets/pincodes.json
# ------------------------------------------------------------

# Set PYTHONPATH
ENV PYTHONPATH=/src/backend:/src
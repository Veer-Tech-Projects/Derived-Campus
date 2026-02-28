FROM python:3.12-slim

WORKDIR /src

# --- CRITICAL CHANGE: SKIP OS UPDATES ---
# We removed 'apt-get update' because it hangs on mobile hotspots.
# Your requirements.txt uses 'psycopg2-binary', so we don't need
# gcc or libpq-dev installed at the system level.
# ----------------------------------------

# Copy requirements
COPY backend/requirements.txt .

# Install Python dependencies
# We use a long timeout (1000s) to be patient with your hotspot
RUN pip install --no-cache-dir --timeout=1000 --retries=10 -r requirements.txt

# Copy source code
COPY backend/ /src/backend/
COPY ingestion/ /src/ingestion/
COPY scripts/ /src/scripts/

# Set PYTHONPATH
ENV PYTHONPATH=/src/backend:/src
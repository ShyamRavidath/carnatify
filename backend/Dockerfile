# Carnatify API — HuggingFace Spaces (Docker SDK).
# Build context is the Space repo root (this backend/ pushed as the Space).
FROM python:3.11-slim

# libsndfile is needed by soundfile/librosa at import time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install CPU-only torch first (much smaller than the default CUDA build),
# then the rest of the requirements.
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Application code + bundled ML assets. These dirs must be present in the Space
# repo (see build_space.sh, which assembles them from the parent project).
COPY . .

# HuggingFace Spaces routes traffic to $PORT (default 7860).
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]

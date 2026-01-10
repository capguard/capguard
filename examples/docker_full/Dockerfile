FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy packaging files
COPY pyproject.toml README.md ./

# Upgrade pip first
RUN pip install --upgrade pip

# Install base dependencies
RUN pip install --no-cache-dir pydantic>=2.0.0

# Install optional dependencies separately to debug
# RUN pip install --no-cache-dir sentence-transformers>=2.2.0 (Skipped: not needed for LLM demo, causing build timeout)
RUN pip install --no-cache-dir openai>=1.0.0 anthropic>=0.3.0
RUN pip install --no-cache-dir langchain langchain-openai

# Copy source code (will be overwritten by volume in dev, but good for build)
COPY src/ ./src/
COPY examples/ ./examples/

# Install the package in editable mode
RUN pip install -e .

CMD ["python", "examples/docker_full/run_demo.py"]

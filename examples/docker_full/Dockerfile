FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy packaging files
COPY pyproject.toml README.md ./

# Install dependencies (including optional)
RUN pip install --no-cache-dir ".[llm,embedding]" langchain langchain-openai

# Copy source code (will be overwritten by volume in dev, but good for build)
COPY src/ ./src/
COPY examples/ ./examples/

# Install the package in editable mode
RUN pip install -e .

CMD ["python", "examples/docker_full/run_demo.py"]

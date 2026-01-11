FROM python:3.9-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY . /app

# Install test dependencies
RUN pip install pytest pytest-asyncio
RUN pip install langchain langchain-openai langchain-community

# Install capguard in editable mode
# This ensures we test the code on disk
RUN pip install -e .

# Run tests
CMD ["pytest", "tests/"]

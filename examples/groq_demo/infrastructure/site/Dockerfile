FROM python:3.9-slim

WORKDIR /app

# Simple HTTP server that serves the content directory
COPY content/ /app/

# Expose non-privileged port
EXPOSE 8080

# Run python simple http server
CMD ["python3", "-m", "http.server", "8080"]

FROM python:3.11-slim

WORKDIR /app

# Install dependencies (PyYAML for docker-compose file parsing)
RUN pip install --no-cache-dir pyyaml

# Copy portal source files
COPY parser.py server.py audit_domains.py index.html data.json ./
COPY assets/ ./assets/

# Default environment configuration
ENV PORT=8040
ENV BASE_DIR=/containers

EXPOSE 8040

CMD ["python3", "server.py"]

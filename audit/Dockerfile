# OSS Audit Tools Container - Optimized for Size
# Target size: <2GB (vs current 4.41GB)
# Focus on most critical tools only

# ====================================
# Stage 1: Essential Python Tools Only  
# ====================================
FROM python:3.11-slim AS python-tools

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

# Install only the most essential Python tools
RUN pip install --no-cache-dir --disable-pip-version-check \
    pylint==3.0.3 \
    flake8==7.0.0 \
    pbr \
    bandit==1.7.5 \
    black==24.1.1 \
    pytest==8.0.0 \
    && rm -rf /root/.cache

# Install semgrep using official method
RUN python -m pip install --no-cache-dir semgrep \
    && rm -rf /root/.cache

# ====================================  
FROM node:18-alpine AS node-tools

# Install critical JS/TS tools only
RUN npm install -g --no-audit --no-fund --production \
    eslint@8.56.0 \
    typescript@5.3.3 \
    && npm cache clean --force

# ====================================
# Stage 2: Minimal Production Runtime
# ====================================
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    NODE_PATH="/usr/lib/node_modules"

# Create non-root user
RUN groupadd -r ossaudit && useradd -r -g ossaudit -u 1000 ossaudit

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy Python tools (most critical for code quality)
COPY --from=python-tools /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-tools /usr/local/bin /usr/local/bin

# Copy essential Node.js tools
COPY --from=node-tools /usr/local/lib/node_modules /usr/lib/node_modules
COPY --from=node-tools /usr/local/bin /usr/lib/node_bin
RUN for tool in eslint tsc; do \
        ln -sf /usr/lib/node_bin/$tool /usr/local/bin/$tool 2>/dev/null || \
        ln -sf /usr/lib/node_modules/.bin/$tool /usr/local/bin/$tool 2>/dev/null || \
        echo "Warning: $tool not found"; \
    done

# Setup workspace
WORKDIR /workspace
RUN mkdir -p /workspace/reports && chown -R ossaudit:ossaudit /workspace

# Switch to non-root user
USER ossaudit

# Minimal health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=2 \
    CMD python --version || exit 1

# Default command
CMD ["/bin/bash"]
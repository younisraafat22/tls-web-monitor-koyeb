# TLS Web Monitor - Koyeb Deployment
# Optimized Docker image for reliable Chrome installation

FROM python:3.11-slim

# TLS Web Monitor - Koyeb Deployment
# Optimized Docker image for reliable Chrome installation

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/google-chrome-stable
ENV DISPLAY=:99
ENV PORT=8000

# Add labels for Koyeb
LABEL org.opencontainers.image.title="TLS Web Monitor"
LABEL org.opencontainers.image.description="TLS Visa Appointment Monitor with Chrome support"
LABEL koyeb.service.type="web"

# Install system dependencies first
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /etc/apt/trusted.gpg.d/google.gpg \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Chrome and its dependencies
RUN apt-get update && apt-get install -y \
    google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Alternative: Install Chrome via direct download if repository fails
RUN if [ ! -f /usr/bin/google-chrome-stable ]; then \
        echo "Chrome repository installation failed, trying direct download..." && \
        wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
        && dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y \
        && rm -f google-chrome-stable_current_amd64.deb; \
    fi

# Verify Chrome installation and create symlinks
RUN google-chrome-stable --version \
    && ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome \
    && ln -sf /usr/bin/google-chrome-stable /usr/local/bin/chrome \
    && which google-chrome-stable \
    && ls -la /usr/bin/google-chrome*

# Set up working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p downloaded_files logs

# Set correct permissions
RUN chmod +x app.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/keep-alive || exit 1

# Start command
CMD ["python", "app.py"]
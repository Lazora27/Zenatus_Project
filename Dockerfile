# Base Image
FROM python:3.10-slim

# Environment Variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ZENATUS_BASE_PATH=/app/Zenatus_Backtester \
    ZENATUS_CONFIG_PATH=/app/Zenatus_Backtester/config/config.yaml

# System Dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    wget \
    curl \
    # TA-Lib dependencies
    && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xvzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Work Directory
WORKDIR /app

# Python Dependencies
# We manually install dependencies to avoid conflicts with strict versions in requirements.txt
# especially contourpy which requires Python >= 3.11 for version 1.3.3
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir \
    ta-lib \
    vectorbt \
    streamlit \
    dash \
    python-json-logger \
    pyyaml \
    pandas \
    numpy \
    scipy \
    matplotlib \
    requests \
    schedule \
    psutil \
    plotly \
    pebble

# Copy Codebase
COPY . /app

# Create Log/Doc Directories
RUN mkdir -p /app/Zenatus_Dokumentation/LOG \
    && mkdir -p /app/Zenatus_Dokumentation/Listing

# Entrypoint Script
COPY Zenatus_Backtester/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose Ports (Streamlit: 8501, Dash: 8050)
EXPOSE 8501 8050

# Set Entrypoint
ENTRYPOINT ["docker-entrypoint.sh"]

# Default Command (Start Orchestrator)
CMD ["python", "/app/Zenatus_Backtester/02_Agents/pipeline_orchestrator.py"]

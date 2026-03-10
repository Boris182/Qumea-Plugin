FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Systempakete + uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Non-root User anlegen
RUN useradd --create-home --home-dir /home/appuser --shell /bin/bash appuser

# Zuerst nur die Dateien kopieren, die für Dependency-Install wichtig sind
COPY pyproject.toml README.md* /app/
COPY src /app/src

# Paket installieren
RUN uv pip install --system .

# Dateirechte setzen
RUN chown -R appuser:appuser /app /home/appuser

USER appuser

# Falls dein Script aus [project.scripts] gestartet werden soll:
CMD ["qumea-plugin"]
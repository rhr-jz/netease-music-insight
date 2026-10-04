FROM node:24-bookworm-slim AS node
FROM python:3.11-slim-bookworm AS builder
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
WORKDIR /app
COPY requirements.txt requirements-online.txt requirements-test.txt pyproject.toml README.md LICENSE ./
COPY netease_music_insight/ ./netease_music_insight/
COPY scripts/prepare_online_api.py scripts/prepare_online_api.py
COPY deploy/netease-package-lock.json deploy/netease-package-lock.json
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements-online.txt && /opt/venv/bin/pip install --no-cache-dir --no-deps .
RUN python scripts/prepare_online_api.py /opt/netease-api

FROM python:3.11-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/netease-api /opt/netease-api
RUN useradd --uid 10001 --create-home insight
USER insight
WORKDIR /home/insight
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MUSIC_INSIGHT_ENV=production MUSIC_INSIGHT_HOST=0.0.0.0 MUSIC_INSIGHT_PORT=8000 \
    MUSIC_INSIGHT_NETEASE_API_DIR=/opt/netease-api MUSIC_INSIGHT_TEMP_ROOT=/tmp/music-insight \
    MUSIC_INSIGHT_LOG_DIR=/tmp/music-insight-logs
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD ["python", "-m", "netease_music_insight.online.healthcheck"]
CMD ["music-insight-online"]

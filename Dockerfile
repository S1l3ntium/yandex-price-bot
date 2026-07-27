FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup --system bot \
    && adduser --system --ingroup bot bot

COPY --chown=bot:bot . .
RUN mkdir -p /app/data /app/backups && chown -R bot:bot /app/data /app/backups

VOLUME ["/app/data", "/app/backups"]

ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/prices.db
ENV BACKUP_DIR=/app/backups
ENV MPLCONFIGDIR=/tmp/matplotlib

USER bot

CMD ["python", "main.py"]

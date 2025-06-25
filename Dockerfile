FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# .env должен быть смонтирован через volume или скопирован отдельно
# База данных будет храниться в volume
VOLUME ["/app/prices_data"]

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"] 
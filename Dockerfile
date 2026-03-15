FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

ENV LOLTRACKER_DB_PATH=/data/loltracker.db

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", \
     "--workers", "2", "--timeout", "1200", "app:app"]

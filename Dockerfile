FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
COPY mail_app ./mail_app
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /data
ENV PORT=8001
ENV MAIL_DB_PATH=/data/accounts.sqlite
EXPOSE 8001
CMD ["sh", "-c", "uvicorn mail_app.app:app --host 0.0.0.0 --port ${PORT:-8001} --proxy-headers"]

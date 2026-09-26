FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
COPY mail_app ./mail_app
COPY start.py .
COPY uvicorn-wrapper.sh /tmp/uvicorn-wrapper.sh
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /data \
    && cp /tmp/uvicorn-wrapper.sh /usr/local/bin/uvicorn \
    && chmod +x /usr/local/bin/uvicorn
ENV PORT=8001
ENV MAIL_DB_PATH=/data/accounts.sqlite
EXPOSE 8001
CMD ["python", "start.py"]

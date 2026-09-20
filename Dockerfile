FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
COPY mail_app ./mail_app
COPY start.py .
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /data
ENV PORT=8001
ENV MAIL_DB_PATH=/data/accounts.sqlite
EXPOSE 8001
CMD ["python", "start.py"]

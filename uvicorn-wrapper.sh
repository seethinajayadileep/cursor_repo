#!/bin/sh
# Railway dashboard may still pass: uvicorn ... --port '${PORT:-8001}'
# Ignore those args and bind using the PORT env var in start.py.
exec python /app/start.py

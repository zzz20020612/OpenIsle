FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY literature_system/requirements-runtime.txt ./requirements-runtime.txt
RUN pip install --no-cache-dir -r requirements-runtime.txt

COPY literature_system/ ./

RUN mkdir -p /app/data /app/logs /app/pdfs

EXPOSE 8088

CMD ["sh", "-c", "python scripts/init_db.py && python code/search/api.py --host 0.0.0.0 --port 8088"]

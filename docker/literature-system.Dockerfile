FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# The integrated service must run the teammate project's complete engine, not
# the former five-package compatibility subset.  Keep requirements.txt as the
# single dependency contract shared by standalone and Docker execution.
COPY literature_system/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY literature_system/ ./

RUN mkdir -p /app/data /app/logs /app/pdfs

EXPOSE 8088

CMD ["sh", "-c", "python scripts/init_db.py && python code/search/api.py --host 0.0.0.0 --port 8088"]

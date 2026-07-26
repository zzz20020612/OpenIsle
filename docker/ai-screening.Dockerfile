FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY ai-screening/paper-screening/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY ai-screening/paper-screening/README.md ai-screening/paper-screening/SKILL.md ./
COPY ai-screening/paper-screening/agents ./agents
COPY ai-screening/paper-screening/references ./references
COPY ai-screening/paper-screening/scripts ./scripts
COPY ai-screening/paper-screening/screening_service ./screening_service

ENV AI_SCREENING_PORT=8090

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').getenv('AI_SCREENING_PORT', '8090') + '/health', timeout=3)"

CMD ["sh", "-c", "uvicorn screening_service.api:app --host 0.0.0.0 --port ${AI_SCREENING_PORT:-8090}"]

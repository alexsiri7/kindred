# Build with: docker build -f web/backend/Dockerfile -t kindred-web-backend .
# (Build context must be the repo root so we can copy ../lib.)
FROM python:3.12-slim

WORKDIR /app

COPY web/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the shared lib as an editable package so imports resolve as `lib.*`.
COPY lib/ /lib/
RUN pip install --no-cache-dir -e /lib

COPY web/backend/ /app/

ENV PYTHONPATH=/app
EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

# Build with: docker build -f mcp/Dockerfile -t kindred-mcp .
# (Build context must be the repo root so we can copy ../prompts.)
FROM python:3.12-slim

WORKDIR /app

COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp/ /app/
COPY prompts/ /prompts/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

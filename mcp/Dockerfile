# Build with: docker build -f mcp/Dockerfile -t kindred-mcp .
# (Build context must be the repo root so we can copy ../prompts and ../lib.)
FROM python:3.12-slim

WORKDIR /app

COPY mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install the shared lib as an editable package so imports resolve as `lib.*`.
COPY lib/ /lib/
RUN pip install --no-cache-dir -e /lib

COPY mcp/ /app/
COPY prompts/ /prompts/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

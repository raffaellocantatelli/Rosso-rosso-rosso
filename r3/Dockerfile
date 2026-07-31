FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY r3/ ./r3/

EXPOSE 8000

CMD ["uvicorn", "r3.node:app", "--host", "0.0.0.0", "--port", "8000"]

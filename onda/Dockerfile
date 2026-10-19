# ONDA/1.0 — immagine degli agenti (RAFFA-001, SENTIN-004, MEMO-002) e degli strumenti.
# Build dal repository: docker build -f onda/Dockerfile -t r3-onda .
FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir "redis>=5,<6" "PyNaCl>=1.5,<2"

# Solo ciò che l'adattatore importa davvero. La memoria vettoriale NON entra
# nell'immagine: MEMO-002 la legge da un volume montato in sola lettura.
COPY sdq1/ ./sdq1/
RUN rm -f sdq1/memory/store.json
COPY onda/ ./onda/

RUN useradd --uid 1000 --no-create-home onda
USER onda
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "onda"]

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .
# Regras tributárias versionadas (lidas pelo motor; versão e hash gravados em cada simulação)
COPY rules ./rules
ENV RULES_DIR=/app/rules

# Configuração somente por variáveis de ambiente (ver .env.example na raiz do projeto).
USER nobody
CMD ["python", "-m", "worker.main"]

# ---- Estágio 1: Construção ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Instala dependências do sistema necessárias para compilar psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Estágio 2: Produção ----
FROM python:3.11-slim

WORKDIR /app

# Instala apenas a libpq (runtime) — sem compiladores
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Copia as dependências instaladas do estágio anterior
COPY --from=builder /install /usr/local

# Copia o código da aplicação
COPY . .

# Cria um usuário não-root para segurança
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# Inicia com Gunicorn (servidor WSGI de produção)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]

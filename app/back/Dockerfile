FROM public.ecr.aws/docker/library/python:3.12-slim

RUN pip install --no-cache-dir "psycopg[binary]==3.2.3"

WORKDIR /app
COPY app.py .

ARG APP_VERSION=1.0
ENV APP_VERSION=${APP_VERSION} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Utilisateur non root : le conteneur respecte la Pod Security « restricted » (TP 09)
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]

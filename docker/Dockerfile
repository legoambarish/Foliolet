# syntax=docker/dockerfile:1.7
# Native linux/arm64 (Apple Silicon) and linux/amd64 (Intel) base images.
FROM node:22-bookworm-slim AS javascript
RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund
COPY spring-boot-service/package.json spring-boot-service/package-lock.json ./spring-boot-service/
RUN --mount=type=cache,target=/root/.npm npm ci --prefix spring-boot-service --omit=optional --no-audit --no-fund
COPY tools/build-frontend-assets.cjs ./tools/
RUN node tools/build-frontend-assets.cjs

FROM maven:3.9.11-eclipse-temurin-17 AS java
WORKDIR /build
COPY spring-boot-service/pom.xml ./
RUN --mount=type=cache,target=/root/.m2 mvn -B dependency:go-offline
COPY spring-boot-service/src ./src
RUN --mount=type=cache,target=/root/.m2 mvn -B -DskipTests package

FROM cloudflare/cloudflared:2026.10.1 AS tunnel

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    NODE_PATH=/app/spring-boot-service/node_modules \
    DJANGO_SETTINGS_MODULE=hermes.settings
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless tesseract-ocr tesseract-ocr-eng fonts-dejavu-core nginx ca-certificates libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY django-service/requirements.txt ./django-service/
COPY tools/requirements-dev.txt tools/requirements-ocr.txt ./tools/
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install \
    -r django-service/requirements.txt -r tools/requirements-dev.txt -r tools/requirements-ocr.txt
COPY --from=javascript /usr/local/bin/node /usr/local/bin/node
COPY --from=javascript /app/spring-boot-service/node_modules ./spring-boot-service/node_modules
COPY --from=java /build/target/dms-0.0.1-SNAPSHOT.jar ./spring-boot-service/app.jar
COPY --from=tunnel /usr/local/bin/cloudflared /usr/local/bin/cloudflared
COPY django-service ./django-service
COPY --from=javascript /app/django-service/dashboard/static/wallet/vendor ./django-service/dashboard/static/wallet/vendor
COPY tools/local-watcher/*.py ./tools/local-watcher/
COPY tools/digilocker-evm.cjs tools/provision-digilocker-trust.cjs tools/ocr-layout-worker.py tools/share-tunnel.py ./tools/
COPY docker ./docker
RUN groupadd --gid 10001 foliolet && useradd --uid 10001 --gid foliolet --create-home foliolet \
    && mkdir -p /app/.local-data /app/imports/foliolet /run/foliolet \
    && chown -R foliolet:foliolet /app/.local-data /run/foliolet \
    && DJANGO_SECRET_KEY=build-only-static-collection-no-runtime-secret STATIC_ROOT=/app/static \
       python django-service/manage.py collectstatic --noinput --verbosity 0 \
    && python tools/ocr-layout-worker.py --check \
    && python -c "import rapidocr, onnxruntime, psycopg, watchdog, waitress" \
    && chmod -R a+rX /app/django-service /app/tools /app/docker /app/spring-boot-service /app/static
USER foliolet
CMD ["python", "/app/docker/runtime.py"]

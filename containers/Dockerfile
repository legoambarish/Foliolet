# syntax=docker/dockerfile:1
FROM node:22-bookworm-slim AS node-build
WORKDIR /work
COPY package*.json ./
COPY spring-boot-service/package*.json ./spring-boot-service/
RUN npm ci --ignore-scripts && npm ci --ignore-scripts --prefix spring-boot-service
COPY spring-boot-service/contracts ./spring-boot-service/contracts
COPY spring-boot-service/scripts ./spring-boot-service/scripts
COPY spring-boot-service/src/test/resources ./spring-boot-service/src/test/resources
COPY tools ./tools
COPY django-service ./django-service
RUN node tools/build-frontend-assets.cjs && node spring-boot-service/scripts/compile-contracts.cjs
RUN NODE_PATH=/work/spring-boot-service/node_modules node --test spring-boot-service/scripts/test-proof-security.cjs spring-boot-service/scripts/test-verifier-ui.cjs tools/test-share-qr.cjs
RUN NODE_PATH=/work/spring-boot-service/node_modules node spring-boot-service/scripts/test-contracts.cjs

FROM maven:3.9.11-eclipse-temurin-17 AS java-build
WORKDIR /work
COPY spring-boot-service/pom.xml ./pom.xml
RUN --mount=type=cache,target=/root/.m2 mvn -B -q dependency:go-offline
COPY spring-boot-service/src ./src
COPY --from=node-build /work/spring-boot-service/src/main/resources/solidity ./src/main/resources/solidity
# Unit tests execute during every clean application-image build.
RUN --mount=type=cache,target=/root/.m2 mvn -B -q package

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NODE_PATH=/app/spring-boot-service/node_modules:/app/node_modules
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-mar tesseract-ocr-osd \
    libglib2.0-0 libgomp1 fonts-dejavu-core ca-certificates curl tini \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY django-service/requirements.txt /app/django-service/requirements.txt
COPY tools/requirements-dev.txt tools/requirements-ocr.txt /app/tools/
RUN pip install --no-cache-dir -r django-service/requirements.txt -r tools/requirements-dev.txt -r tools/requirements-ocr.txt
COPY --from=node-build /usr/local/bin/node /usr/local/bin/node
COPY --from=node-build /work/spring-boot-service/node_modules /app/spring-boot-service/node_modules
COPY --from=node-build /work/node_modules /app/node_modules
COPY django-service /app/django-service
COPY tools /app/tools
COPY containers /app/containers
COPY --from=node-build /work/django-service/dashboard/static/wallet/vendor /app/django-service/dashboard/static/wallet/vendor
COPY --from=java-build /work/target/dms-0.0.1-SNAPSHOT.jar /app/service.jar
RUN python -I tools/ocr-layout-worker.py --check \
    && FOLIOLET_STATE_DIR=/tmp/foliolet-build-check python django-service/manage.py test dashboard --noinput \
    && python tools/test-intake-watcher.py \
    && python tools/test-ocr-layout-worker.py \
    && python containers/test_container_config.py \
    && rm -rf /tmp/foliolet-build-check \
    && useradd --uid 1000 --create-home foliolet
USER 1000:1000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "/app/containers/frontend.py"]

FROM runtime AS acceptance
USER 0:0
COPY tools/requirements-foli-test.txt /app/tools/requirements-foli-test.txt
RUN pip install --no-cache-dir -r tools/requirements-foli-test.txt
USER 1000:1000

# CI can export actual Surefire results without copying Maven into the runtime.
FROM scratch AS java-test-results
COPY --from=java-build /work/target/surefire-reports /surefire

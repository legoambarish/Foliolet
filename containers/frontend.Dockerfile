FROM python:3.12-slim AS dependencies
WORKDIR /build
COPY django-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt gunicorn==23.0.0
FROM python:3.12-slim
COPY --from=dependencies /install /usr/local
RUN groupadd --gid 1000 foliolet && useradd --uid 1000 --gid 1000 --create-home foliolet && mkdir /state && chown foliolet:foliolet /state
WORKDIR /app
COPY django-service ./
COPY containers/frontend-entrypoint.sh /entrypoint.sh
USER foliolet
ENTRYPOINT ["sh", "/entrypoint.sh"]

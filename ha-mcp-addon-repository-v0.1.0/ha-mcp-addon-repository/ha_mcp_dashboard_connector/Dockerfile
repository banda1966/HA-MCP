ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN addgroup -S app && adduser -S -G app app \
    && mkdir -p /app /data \
    && chown -R app:app /app /data
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
COPY run.sh ./run.sh
RUN chmod 755 ./run.sh && chown -R app:app /app
USER app
EXPOSE 8099
CMD ["./run.sh"]

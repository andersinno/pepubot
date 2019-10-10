FROM python:3.7-slim AS builder
WORKDIR /app
COPY requirements-*.txt ./
RUN \
        sed -i -e 's/^-e .$//' requirements-dev.txt && \
        pip wheel --no-cache-dir -w /wheels -r requirements-dev.txt && \
        pip wheel --no-cache-dir -w /wheels -r requirements-style.txt && \
        pip wheel --no-cache-dir -w /wheels -r requirements-test.txt && \
        pip wheel --no-cache-dir -w /wheels -r requirements-typing.txt && \
        echo Wheels rolled.
COPY . .
RUN pip wheel --no-cache-dir -w /wheels .

##############################################################################
FROM python:3.7-slim AS dev
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY . .
RUN pip install --no-cache-dir -f /wheels -e .
ENTRYPOINT ["pepubot"]

##############################################################################
FROM python:3.7-slim AS prod-installer
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY . .
RUN pip install --no-cache-dir -f /wheels .

##############################################################################
FROM python:3.7-slim AS prod
WORKDIR /app
COPY --from=prod-installer /usr/local/bin /usr/local/bin
COPY --from=prod-installer /usr/local/lib/python3.7 /usr/local/lib/python3.7
ENTRYPOINT ["pepubot"]

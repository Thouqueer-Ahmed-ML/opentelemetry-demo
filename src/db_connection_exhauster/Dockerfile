# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0


FROM docker.io/library/python:3.12-alpine3.22 AS build-venv
RUN apk update && apk add gcc g++ linux-headers
COPY ./src/db_connection_exhauster/requirements.txt requirements.txt
RUN python -m venv venv && venv/bin/pip install --no-cache-dir -r requirements.txt

FROM docker.io/library/python:3.12-alpine3.22
COPY --from=build-venv /venv/ /venv/
WORKDIR /app
COPY ./src/db_connection_exhauster/__init__.py __init__.py
COPY ./src/db_connection_exhauster/main.py main.py
ENTRYPOINT ["/venv/bin/python", "main.py" ]

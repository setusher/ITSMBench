FROM python:3.12-slim-bullseye
RUN pip install --no-cache-dir pytest==8.4.1 requests==2.32.3
WORKDIR /work

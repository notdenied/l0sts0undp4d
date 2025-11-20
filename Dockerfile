FROM python:3.13-slim

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app
COPY app.py requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7331

ENTRYPOINT ["/entrypoint.sh"]

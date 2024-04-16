FROM alpine:latest

ARG TOPIC_MANAGER_PORT
ENV SERVER_PORT="0.0.0.0:$TOPIC_MANAGER_PORT"

WORKDIR /app

COPY . .

RUN apk add --update py3-pip py3-setuptools python3-dev

RUN apk add --update gcc musl-dev librdkafka-dev

RUN pip3 install -r requirements.txt  --break-system-packages --no-cache-dir

EXPOSE $TOPIC_MANAGER_PORT

CMD gunicorn -k gevent --bind ${SERVER_PORT} topic_manager:app
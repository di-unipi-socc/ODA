FROM arm64v8/python:latest

ARG K_ADMIN_PORT
ENV SERVER_PORT="0.0.0.0:$K_ADMIN_PORT"

WORKDIR /app

COPY . .

# RUN apk add --update py3-pip py3-setuptools python3-dev

# RUN apk add --update gcc musl-dev librdkafka-dev

# RUN pip3 install -r requirements.txt  --break-system-packages --no-cache-dir

RUN pip3 install -r requirements.txt --no-cache-dir

EXPOSE $K_ADMIN_PORT

CMD gunicorn -k gevent --bind ${SERVER_PORT} k_admin:app
FROM alpine

ARG API_GATEWAY_PORT
ENV SERVER_PORT="0.0.0.0:$API_GATEWAY_PORT"

WORKDIR /app

COPY . .

RUN apk add --update py3-pip

RUN apk add --update py3-setuptools

RUN pip3 install -r requirements.txt  --break-system-packages --no-cache-dir

EXPOSE $API_GATEWAY_PORT

CMD gunicorn -k gevent --bind ${SERVER_PORT} api_gateway:app
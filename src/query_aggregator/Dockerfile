FROM alpine

ARG QUERY_AGGREGATOR_PORT
ENV SERVER_PORT="0.0.0.0:$QUERY_AGGREGATOR_PORT"

WORKDIR /app

COPY . .

RUN apk add --update py3-pip

RUN apk add --update py3-setuptools

RUN pip3 install -r requirements.txt  --break-system-packages --no-cache-dir

EXPOSE $QUERY_AGGREGATOR_PORT

CMD gunicorn -k gevent --bind ${SERVER_PORT} query_aggregator:app
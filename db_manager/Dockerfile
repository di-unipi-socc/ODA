FROM alpine

ARG DB_MANAGER_PORT
ENV SERVER_PORT="0.0.0.0:$DB_MANAGER_PORT"

WORKDIR /app

COPY . .

RUN apk add --update py3-pip

RUN apk add --update py3-setuptools

RUN pip3 install -r requirements.txt  --break-system-packages --no-cache-dir

EXPOSE $DB_MANAGER_PORT

CMD gunicorn -k gevent --bind ${SERVER_PORT} db_manager:app --workers 6
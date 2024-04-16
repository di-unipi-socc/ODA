FROM alpine:latest

WORKDIR /app

COPY . .

RUN apk add --update py3-pip py3-setuptools python3-dev

RUN apk add --update gcc musl-dev librdkafka-dev

RUN pip3 install -r requirements.txt --break-system-packages --no-cache-dir

CMD ["python3", "data_harvester.py"]

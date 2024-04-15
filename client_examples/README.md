# DATA GENERATOR AND DATA CONSUMER EXAMPLES

Here we provide two examples of Data Generators and Data Consumers using Python. The examples use the Kafka client provided by the [Confluent Kafka Python client](https://docs.confluent.io/kafka-client/overview.html).

## Prerequisites

* Python 3.6 or higher.

## Data Generator

To run the Data Generator, navigate to the `example` folder and run the following command:

```python ODA_DG.py``` with the following options:

```bash
ODA_DG.py [-h] [--number_of_msg NUMBER_OF_MSG] [--registered REGISTERED] [--apigateway APIGATEWAY]
                 [--data DATA] [--topic TOPIC] [--generator_id GENERATOR_ID] [--timestamp TIMESTAMP]
                 [--topics [TOPICS ...]] [--timeout TIMEOUT]

options:
  -h, --help            show the help message and exit
  --number_of_msg NUMBER_OF_MSG, -n NUMBER_OF_MSG
                        Set the number of messages to send, default: 1
  --registered REGISTERED, -r REGISTERED
                        Set the Kafka endpoint if registered previously
  --apigateway APIGATEWAY, -a APIGATEWAY
                        Set the API Gateway URL, default: http://127.0.0.1:50005
  --data DATA, -d DATA  Set the data to send, default: generated randomly
  --topic TOPIC, -tp TOPIC
                        Set the topic of the data, default: generated randomly
  --generator_id GENERATOR_ID, -g GENERATOR_ID
                        Set the generator_id of the data, default: "generic_generator"
  --timestamp TIMESTAMP, -ts TIMESTAMP
                        Set the timestamp of the data (format: YY-mm-ddThh:mm:ssZ), default "datetime.now"
  --topics [TOPICS ...], -tps [TOPICS ...]
                        List of topic names to subscribe to, default: "generic_topic"
  --timeout TIMEOUT, -t TIMEOUT
                        Set the sending packet in timeout in seconds, default: 0
```

### Example: sending a message

```python ODA_DG.py -tp livingroom -d "{'temperature': 25, 'humidity': 50}" -g livingroom_termometer```
will register to the API Gateway with the topic `livingroom` and will send the message:

```json
"timestamp": <current time>,
"generator_id": "livingroom_termometer",
"topic": "livingroom",
"data": "{'temperature': 25, 'humidity': 50}",
```

### Example: sending generated messages

```python ODA_DG.py -n 10 -tps livingroom kitchen -g livingroom_termometer``` will register to the API Gateway with the topics `livingroom` and `kitchen` and will send 10 messages with random data to selecting randomly those two topics.

## Data Consumer

To run the Data Consumer, navigate to the `example` folder and run the following command:

```python ODA_DC.py``` with the following options:

```ODA_DC.py [-h] [--register REGISTER] [--apigateway APIGATEWAY] [--timeout TIMEOUT]
                 topics [topics ...]

positional arguments:
  topics                List of topic names to subscribe to

options:
  -h, --help            show this help message and exit
  --register REGISTER, -r REGISTER
                        Set the Kafka endpoint if registered previously
  --apigateway APIGATEWAY, -a APIGATEWAY
                        Set the API Gateway URL
  --timeout TIMEOUT, -t TIMEOUT
                        Set the polling timeout
```

### Example: receiving messages

```python ODA_DC.py livingroom kitchen``` will register to the API Gateway with the topics `livingroom` and `kitchen` and will print the messages received from those topics. The program will run until the user stops it with a keyboard interrupt.

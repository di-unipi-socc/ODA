# DATA GENERATOR AND DATA CONSUMER EXAMPLES

Here we provide two examples of Data Generators and Data Consumers using Python. The examples use the Kafka client provided by the [Confluent Kafka Python client](https://docs.confluent.io/kafka-client/overview.html).

## Prerequisites

* Python 3.10 or higher.
* Confluent Kafka Python module version 2.3.0 or higher. To install it, run the following command:

```bash
pip install confluent_kafka
```

## Data Generator

The Data Generator can create random data or send a specific messages to a specific topic.

The DG will register to the API Gateway and will send the message to the Kafka topic provided. The generator will run until the number of messages provided by the user is sent.

It is possible to specify the time interval between messages and avoid the registration to the API Gateway by providing the Kafka endpoint.

### DG client execution

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

### Writing an ODA DG

To write an ODA DG is necessary to use a [Kafka producer client](https://docs.confluent.io/platform/current/clients/index.html).

The DG must register to the API Gateway following the [ODA API](../README.md) by providing the topics it will use to send messagges and it will receive the Kafka endpoint.

The producer is created using the Kafka endpoint provided by the API Gateway and can send messages to Kafka using the topics provided to the API Gateway.

The data will be stored in the ODA database if the data format is correct.

## Data Consumer

The data consumer runs until the user stops it with a keyboard interrupt. It will register to the API Gateway and will subscribe to the topics provided by the user contained in Kafka.

If none of the provided topics is contained in Kafka, the client will stop the execution. Otherwise, it will print the messages received from those topics.

It is possible to specify the polling time interval and avoid the registration to the API Gateway by providing the Kafka endpoint.

Running multiple Data Consumers with the same group_id create a consumer group. The messages will be distributed among the consumers in the group.

Using the `--group_instance_id` option, it is possible to set a static id for the consumer in the group. This way, the consumer will be recognised by Kafka and will receive its own messages, even if it is restarted.

### DC client execution

To run the Data Consumer, navigate to the `example` folder and run the following command:

```python ODA_DC.py``` with the following options:

```ODA_DC.py [-h] [--register REGISTER] [--apigateway APIGATEWAY] [--timeout TIMEOUT]
                 [--group_id GROUP_ID] [--group_instance_id GROUP_INSTANCE_ID]
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
  --group_id GROUP_ID, -g GROUP_ID
                        Kafka consumer group id
  --group_instance_id GROUP_INSTANCE_ID, -gi GROUP_INSTANCE_ID
                        Set the consumer static id
```

### Example: receiving messages

```python ODA_DC.py livingroom kitchen``` will register to the API Gateway with the topics `livingroom` and `kitchen` and will print the messages received from those topics. The program will run until the user stops it with a keyboard interrupt.

### Writing an ODA DC

To write an ODA DC is necessary to use a [Kafka consumer client](https://docs.confluent.io/platform/current/clients/index.html).

The DC must register to the API Gateway following the [ODA API](../README.md) and it will receive the topics avilable in ODA and the Kafka endpoint.

To create a Kafka consumer are needed the following parameters:
    - the Kafka enpoint,
    - the group identifier,
    - the policy to reset the Kafka offset.
After every message received, the consumer has to commit the offset to Kafka.

The consumer will receive the messages from the subscribed topics.

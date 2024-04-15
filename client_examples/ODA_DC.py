from confluent_kafka import Consumer, KafkaException
import json,requests, logging, sys
from time import sleep
from argparse import ArgumentParser

#GROUP_INSTANCE_ID = 'consumer_group_instance' #EACH CONSUMER MUST HAVE A UNIQUE GROUP INSTANCE ID TO BE REMBERED BY KAFKA
GROUP_ID = 'consumer_group' #TO RECEIVE ALL THE MESSAGE IT MUST BE ALONE IN THE GROUP
AUTO_OFFSET_RESET = 'earliest' #TO RECEIVE ALL THE MESSAGE STORED IN KAFKA
AUTO_COMMIT_INTERVAL_MS = '1000' #TO COMMIT THE OFFSET EVERY SECOND

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Parse command-line arguments
parser = ArgumentParser(prog='ODA_DC.py',
                    description='Data consumer for and ODA service.')
parser.add_argument('topics', type=str, nargs='+', help='List of topic names to subscribe to')
parser.add_argument('--register', '-r', help='Set the Kafka endpoint if registered previously')
parser.add_argument('--apigateway', '-a', help='Set the API Gateway URL', default="http://127.0.0.1:50005")
parser.add_argument('--timeout', '-t', help='Set the polling timeout', default=1)
args = parser.parse_args()

# Initialize variables from command-line arguments
_topics = args.topics
API_GATEWAY_URL = args.apigateway
_TIMEOUT = int(args.timeout)

# Check if the Kafka endpoint is provided as an argument otherwise register to the API Gateway
if args.register:
    KAFKA_ENDPOINT = args.register
else:
    try:
        logging.info("Registering to API Gateway...")
        x = requests.get(API_GATEWAY_URL + f'/register/dc')
        x.raise_for_status()
        msg = x.json()
        KAFKA_ENDPOINT = msg["KAFKA_ENDPOINT"]
        topics = msg["topics"]
        print(f"Obtained KAFKA_ENDPOINT: {KAFKA_ENDPOINT}")
        print(f"Obtained topics: {topics}")
    except Exception as e:
        logging.info(repr(e))
        exit(1)

    # Check if the topics to subscribe are registered in ODA
    t = False
    for topic in _topics:
        if topic not in topics:
            logging.warning(f"Topic \"{topic}\" not registered")
            _topics.remove(topic)
        else:
            t = True

    if not t:
        logging.error("No registered topics")
        exit(1)

logging.info("Initializing consumer...")
c= Consumer({
    'bootstrap.servers': KAFKA_ENDPOINT,
    'group.id': GROUP_ID,
    'auto.offset.reset': AUTO_OFFSET_RESET,
    'auto.commit.interval.ms': AUTO_COMMIT_INTERVAL_MS
})
try:
    logging.info(f"Subscribing to topics {_topics}")
    c.subscribe(_topics)
except KafkaException as ke:
    logging.error(f"KafkaException: {repr(ke)}")

logging.info("Starting polling from kafka...")
while True:
    sleep(_TIMEOUT)
    msg = c.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        logging.error("Message error: {}".format(msg.error()))
        continue
    try:
        logging.info("Received message")
        logging.info(json.loads(msg.value().decode('utf-8')))
    except Exception as e:
        logging.error(f'Exception: {repr(e)}')
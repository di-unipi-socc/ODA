from confluent_kafka import Producer
import json, random, time, requests, sys, logging
from datetime import datetime, timezone
from argparse import ArgumentParser

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


# Parse command-line arguments
parser = ArgumentParser(prog='ODA_DG.py',
                    description='Data Generator for and ODA service.')

parser.add_argument('--number_of_msg', '-n', type=int, help='Set the number of messages to send, default: 1', default=1)
parser.add_argument('--registered', '-r', help='Set the Kafka endpoint if registered previously')
parser.add_argument('--apigateway', '-a', help='Set the API Gateway URL, default: http://127.0.0.1:50005', default="http://127.0.0.1:50005")
#Fields to send to ODA
parser.add_argument('--data', '-d', help='Set the data to send, default: generated randomly', default=None)
parser.add_argument('--topic', '-tp', help='Set the topic of the data, default: generated randomly', default=None)
parser.add_argument('--generator_id', '-g', help='Set the generator_id of the data, default: "generic_generator"', default="generic_generator")
parser.add_argument('--timestamp', '-ts',  help='Set the timestamp of the data (format: YY-mm-ddThh:mm:ssZ), default "datetime.now"', default=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
#Topics to generate random data
parser.add_argument('--topics', '-tps', type=str, nargs='*', help='List of topic names to subscribe to, default: "generic_topic"', default=["generic_topic"])
parser.add_argument('--timeout', '-t', type=int, help='Set the sending packet in timeout in seconds, default: 0', default=0)

args = parser.parse_args()

# Initialize variables from command-line arguments
_TIMEOUT_MSGS = int(args.timeout)
registered = args.registered
API_GATEWAY_URL = args.apigateway
n_msg = int(args.number_of_msg)

data = args.data or None
topic = args.topic or None
generator_id = args.generator_id
timestamp = args.timestamp

topics = args.topics

# Check if the Kafka endpoint is provided as an argument otherwise register to the API Gateway
if registered:
    KAFKA_ENDPOINT = registered
else:
    try:
        logging.info("Registering to API Gateway...")
        if topic:
            msg = {"topics": [topic]} 
        else:
            msg = {"topics": topics}
        logging.info(f"Registering topics: {msg}")
        x = requests.post(API_GATEWAY_URL + f'/register/dg', json=msg)
        x.raise_for_status()
        msg = x.json()
        KAFKA_ENDPOINT = msg["KAFKA_ENDPOINT"]
        logging.info(f"Obtained KAFKA_ENDPOINT: {KAFKA_ENDPOINT}")
    except Exception as e:
        logging.info(repr(e))
        exit(1)

# Generate random data if not provided for each message to send
def generate_data():
    data = {}
    if random.randint(0, 1) == 1:
        temp = random.randint(20, 22)
        data["Air temperature indoor"] = {"value": temp,"unit":"C"}
    if random.randint(0, 1) == 1:
        umidity = random.randint(40, 60)
        data["Relative umidity"] = {"value": umidity,"unit":"%"}
    if random.randint(0, 1) == 1:
        illuminance = random.randint(500, 750)
        data["Illuminance"] = {"value": illuminance,"unit":"Lux"}
    if random.randint(0, 1) == 1:
        co2 = random.randint(800, 1000)
        data["CO2 concentration"] = {"value": co2,"unit":"ppm"}
    if random.randint(0, 1) == 1:
        movement = random.randint(0, 1)
        data["Movement/presence"] = {"value": movement,"unit":"0/1"}
    if not data:
        temp = random.randint(20, 22)
        data["Air temperature indoor"] = {"value": temp,"unit":"C"}
    return str(data).replace("'", "\"") # Convert to string and replace single quotes with double quotes to make it valid JSON

# Create a packet with the data to send
def create_packet(timestamp, generator_id, topic, data):
    packet = {
        "timestamp": timestamp,#ex: "2024-01-25T13:53:54Z"
        "generator_id": generator_id,
        "topic": topic,
        "data": data
    }
    return packet

# Delivery report callback after the message has been delivered to Kafka
def delivery_report(err, msg):
    """ Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        logging.info('Message delivery failed: {}'.format(err))
    else:
        value = msg.value().decode('utf-8')
        logging.info(f'Message delivered to {msg.topic()}: {value}')

# Initialize the Kafka producer
p = Producer({'bootstrap.servers': KAFKA_ENDPOINT})
logging.info("Connected to Kafka")

# Send the messages
for i in range(1,n_msg+1):
    
    time.sleep(_TIMEOUT_MSGS)

    p.poll(0)
    # Generate random data if not provided for each message to send
    if not data:
        data = generate_data()
    # Chose a topic randomly if not provided for each message to send
    if not topic:
        topic = random.choice(topics)
    
    packet = create_packet(timestamp, generator_id, topic, data)
    toSend = json.dumps(packet,indent=4)
    # Asynchronously produce a message. The delivery report callback will
    # be triggered from the call to poll() above, or flush() below, when the
    # message has been successfully delivered or failed permanently.
    logging.info(f'Sending message n {i}...')
    p.produce(packet["topic"], toSend.encode('utf-8'), callback=delivery_report)
# Wait for any outstanding messages to be delivered and delivery report
# callbacks to be triggered.
    p.flush()
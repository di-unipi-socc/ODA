from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient
import json, signal, requests, logging, sys, os, concurrent.futures, asyncio

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

#OTHER SERVICES CONFIGURATION
KAFKA_PORT= os.environ["KAFKA_INTERNAL_PORT"]
DB_MANAGER_PORT= os.environ["DB_MANAGER_PORT"]
DB_SERVICE_URL = "http://dbmanager:"+DB_MANAGER_PORT
KAFKA_SERVICE_URL = "kafka:"+KAFKA_PORT

#CONSUMER CONFIGURATION
GROUP_INSTANCE_ID = 'dataservicegroup' #EACH CONSUMER MUST HAVE A UNIQUE GROUP INSTANCE ID TO BE REMBERED BY KAFKA
CLIENT_ID = 'dataservice'
GROUP_ID = 'dataservicegroupid' #TO RECEIVE ALL THE MESSAGE IT MUST BE ALONE IN THE GROUP
AUTO_OFFSET_RESET = 'earliest' #TO RECEIVE ALL THE MESSAGE STORED IN KAFKA
AUTO_COMMIT_INTERVAL_MS = '250' #COMMIT OFFSET INTERVAL (IN MILLISECONDS)

#POLLING TIMEOUT
_TIMEOUT = 10
#SUBSCRIPTION TO ALL TOPICS TIMEOUT
_SUBSCRIBE_TIMEOUT = 60

c= Consumer({
    'bootstrap.servers': KAFKA_SERVICE_URL,
    'group.instance.id': GROUP_INSTANCE_ID, 
    'group.id': GROUP_ID,
    'auto.offset.reset': AUTO_OFFSET_RESET,
    'auto.commit.interval.ms': AUTO_COMMIT_INTERVAL_MS
})


#HANDLER FOR SIGINT
def handler(sig, frame):
    logging.info("Stopping consumer...")
    c.unsubscribe()
    c.close()
    exit(0)
    
signal.signal(signal.SIGINT, handler)

#KAFKA ADMIN CLIENT TO RETRIEVE ALL THE TOPICS
admin = AdminClient({'bootstrap.servers': KAFKA_SERVICE_URL})

#KAFKA CONSUMER TO SUBSCRIBE TO ALL TOPICS AND SEND MESSAGES TO DB SERVICE

#LIST OF TOPICS ALREADY SUBSCRIBED
sub_topics = []
#FUNCTION TO SUBSCRIBE TO ALL THE TOPICS (EXCEPT __consumer_offsets WHICH IS A KAFKA INTERNAL TOPIC)
#ASYNCRONOUS RESPECT TO THE MAIN LOOP
async def subscribeAll():
    logging.info("Starting subscription routine...")
    while True:
        try:
            await asyncio.sleep(_SUBSCRIBE_TIMEOUT)
            dict = admin.list_topics().topics
            for topic in dict.keys():
                if topic not in sub_topics and topic != "__consumer_offsets":
                    sub_topics.append(topic)
            if sub_topics:
                c.subscribe(sub_topics)
                logging.info(f"Subscribed to {sub_topics}")
        except Exception as e:
            logging.error(f'Exception: {repr(e)}')
#FUNCTION TO SEND THE MSG TO THE DB SERVICE
def sendToDB(msg):
    x = requests.post(DB_SERVICE_URL + f'/writeDB', json=json.loads(msg))
    x.raise_for_status()
#CALLBACK FOR THE THREAD
def threadCallback(future):
    try:
        future.result()
    except Exception as e:
        logging.error(f'Exception: {repr(e)}')
#FUNCTION IMPLMENTING THE MAIN LOOP
'''
Every _SUBSCRIBE_TIMEOUT seconds, the consumer retrieves all the topics from Kafka and subscribes to all of them.
Every _TIMEOUT seconds, the consumer poll msgs from Kafka.
Every new msg is sent to the DB service using a different thread.
Bad formatted msgs are checked by the DB service and will return a 400 status code which generate an exception in the consumer.
'''
async def main():
    logging.info("Starting main loop...")
    asyncio.create_task(subscribeAll())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        msg = None
        while True:
            await asyncio.sleep(_TIMEOUT)
            if sub_topics:
                msg = c.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logging.error("Message error: {}".format(msg.error()))
                continue
            try:
                payload = msg.value().decode('utf-8')
            except Exception as e:
                logging.error(f'Exception: {repr(e)}')
                continue
            future = executor.submit(sendToDB,payload)
            future.add_done_callback(threadCallback)
#START THE MAIN LOOP
asyncio.run(main())
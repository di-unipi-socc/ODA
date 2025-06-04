from flask import Flask, request, make_response, jsonify
from confluent_kafka.admin import AdminClient, NewTopic
import logging, sys, os, json

#CONFIGURATION
KAFKA_PORT= os.environ["KAFKA_INTERNAL_PORT"]
KAFKA_URL = "kafka:"+KAFKA_PORT

RESTORE_TOPICS = os.environ.get("RESTORE_TOPICS", "false").lower() == "true"
TOPICS_FILE = "/app/topiclist/topics.json"

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

admin = AdminClient({'bootstrap.servers': KAFKA_URL})
topics = list(admin.list_topics().topics.keys())
if "__consumer_offsets" in topics:
    topics.remove("__consumer_offsets")

if RESTORE_TOPICS:
    #Restore topics from file
    try:
        if not os.path.exists(TOPICS_FILE):
            with open(TOPICS_FILE, "w") as f:
                json.dump({"topics": topics}, f)
        with open(TOPICS_FILE, "r") as f:
            topics = json.load(f)["topics"]
            if topics:
                new_topics = [NewTopic(topic) for topic in topics]
                admin.create_topics(new_topics)
    except Exception as e:
        app.logger.error(repr(e))
        raise e
    app.logger.info(f"Restored topics from file: {topics}")

@app.route("/register", methods=["POST"]) 
def register():
    msg = request.get_json()
    if not msg:
        return make_response("Empty Registration", 400)
    new_topics = []
    #Received new topics
    rec_topics = msg["topics"]
    #Add new topics to the list and select new topics
    for topic in rec_topics:
        if topic not in topics:
            topics.append(topic)
            new_topics.append(NewTopic(topic))
    #Add new topics to Kafka
    try:
        if new_topics:
            admin.create_topics(new_topics)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 400)  

    #Add new topics to the file
    try:
        with open(TOPICS_FILE, "w") as f:
            json.dump({"topics": topics}, f)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 500)
    return make_response("",200)  
           
@app.route("/topics", methods=["GET"]) 
def get_topics():
    return make_response(json.dumps({"topics": topics}), 200)
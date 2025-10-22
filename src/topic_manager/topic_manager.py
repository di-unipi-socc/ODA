from flask import Flask, request, make_response, jsonify
from confluent_kafka.admin import AdminClient, NewTopic
import logging, sys, os, json

# CONFIGURATION
KAFKA_PORT = os.environ["KAFKA_INTERNAL_PORT"]
KAFKA_URL = "kafka:" + KAFKA_PORT

RESTORE_TOPICS = os.environ.get("RESTORE_TOPICS", "false").lower() == "true"
TOPICS_FILE = "/app/topiclist/topics.json"

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

def _save_topics_atomically(topics_list):
    """Write {"topics": [...]} atomically to avoid truncated/empty files."""
    dirpath = os.path.dirname(TOPICS_FILE) or "."
    os.makedirs(dirpath, exist_ok=True)
    tmp = TOPICS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"topics": topics_list}, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, TOPICS_FILE)  # atomic on POSIX

def _load_topics_safe(default_list):
    """
    Read topics from file. If the file is missing, empty, or invalid JSON,
    return default_list instead of raising.
    """
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
        if not raw:
            app.logger.warning("Topics file is empty; falling back to default.")
            return default_list
        data = json.loads(raw)
        t = data.get("topics", [])
        if isinstance(t, list):
            return t
        app.logger.warning("Invalid 'topics' structure; falling back to default.")
        return default_list
    except FileNotFoundError:
        app.logger.warning("Topics file not found; falling back to default.")
        return default_list
    except Exception as e:
        app.logger.error("Error reading topics file: %r; falling back to default.", e)
        return default_list

admin = AdminClient({'bootstrap.servers': KAFKA_URL})
topics = list(admin.list_topics().topics.keys())
if "__consumer_offsets" in topics:
    topics.remove("__consumer_offsets")

if RESTORE_TOPICS:
    # Restore topics from file (with atomic write + safe read)
    try:
        if not os.path.exists(TOPICS_FILE):
            _save_topics_atomically(topics)
        topics = _load_topics_safe(default_list=topics)
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
    # Received new topics
    rec_topics = msg["topics"]
    # Add new topics to the list and select new topics
    for topic in rec_topics:
        if topic not in topics:
            topics.append(topic)
            new_topics.append(NewTopic(topic))
    # Add new topics to Kafka
    try:
        if new_topics:
            admin.create_topics(new_topics)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 400)

    # Add new topics to the file (atomic)
    try:
        _save_topics_atomically(topics)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 500)
    return make_response("", 200)

@app.route("/topics", methods=["GET"])
def get_topics():
    return make_response(json.dumps({"topics": topics}), 200)

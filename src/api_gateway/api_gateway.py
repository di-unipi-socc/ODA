from flask import Flask, request, make_response, jsonify
import logging, sys, os, requests, json
from requests.exceptions import HTTPError

#CONFIGURATION
DB_MANAGER_PORT= os.environ["DB_MANAGER_PORT"]
QUERY_AGGREGATOR_PORT= os.environ["QUERY_AGGREGATOR_PORT"]
KAFKA_PORT= os.environ["KAFKA_PORT"]
KAFKA_PORT_STATIC= os.environ["KAFKA_PORT_STATIC"]
KAFKA_ADDRESS= os.environ["KAFKA_ADDRESS"]
KAFKA_ADDRESS_STATIC = os.environ["KAFKA_ADDRESS_STATIC"]

DB_MANAGER_URL = "http://dbmanager:"+DB_MANAGER_PORT
QUERY_AGGREGATOR_URL = "http://queryaggregator:"+QUERY_AGGREGATOR_PORT
KAFKA_URL = KAFKA_ADDRESS+":"+KAFKA_PORT
KAFKA_STATIC_URL = KAFKA_ADDRESS_STATIC+":"+KAFKA_PORT_STATIC

TOPIC_MANAGER_PORT= os.environ["TOPIC_MANAGER_PORT"]
TOPIC_MANAGER_URL = "http://topicmanager:"+TOPIC_MANAGER_PORT

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


#QUERY DB SERVICE
'''
The payload for a query must be a JSON having at least one of the following fields:
"start": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ
"stop": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ
"topic": string
"generator_id": string

The response is an unsorted JSON array with all the records that match the query.
Each record has the following structure:
{
    "timestamp": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ,
    "generator_id": string
    "topic": string
    "data": str
'''
@app.route("/query", methods=["POST"]) 
def query():
    try:
        msg = request.get_json()
        app.logger.info(f"Received query: {msg}")
        if not msg:
            return make_response("Empty query", 404)
        if "aggregator" in msg:
            URL = QUERY_AGGREGATOR_URL + '/query'
        else:
            URL= DB_MANAGER_URL + '/query'
        app.logger.info(f"Sending query to {URL}")
        app.logger.info(f"Query: {msg}")
        x = requests.post(URL, json=msg, stream=True)
        x.raise_for_status()
        logging.info("Query sent")
        resp = make_response(x.raw.read(), x.status_code, x.headers.items())
        return resp
        
        #return make_response(x.json(), 200)
    except HTTPError as e:
        app.logger.error(f'HTTP error occurred: {e.response.url} - {e.response.status_code} - {e.response.text}')
        return make_response(e.response.text, e.response.status_code)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 500)
    
@app.route("/register/dc", methods=["GET"]) 
def register_dc():
    try:
        static_param = request.args.get('static', default=None, type=str)
        static_param = static_param.lower() == 'true' if static_param else False
        URL= TOPIC_MANAGER_URL + '/topics'
        app.logger.info(f"Asking for topics to {URL}")
        x = requests.get(URL)
        x.raise_for_status()
        app.logger.info(f"Topics received: {x.content.decode('utf-8')}")
        resp = {}
        resp = json.loads(x.content.decode('utf-8'))
        if static_param:
            resp["KAFKA_ENDPOINT"]=KAFKA_STATIC_URL
        else:
            resp["KAFKA_ENDPOINT"]=KAFKA_URL
        return make_response(json.dumps(resp), 200)
    except HTTPError as e:
        app.logger.error(f'HTTP error occurred: {e.response.url} - {e.response.status_code} - {e.response.text}')
        return make_response(e.response.text, e.response.status_code)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 500)
@app.route("/register/dg", methods=["POST"]) 
def register_dg():
    try:
        static_param = request.args.get('static', default=None, type=str)
        static_param = static_param.lower() == 'true' if static_param else False
        msg = request.get_json()
        if not msg:
            return make_response("Empty Registration", 400)
        URL= TOPIC_MANAGER_URL + '/register'
        app.logger.info(f"Sending registration to {URL}")
        app.logger.info(f"Registration topics: {msg}")
        x = requests.post(URL, json=msg)
        x.raise_for_status()
        logging.info("Registration sent to K Admin")
        if static_param:
            URL_TO_SEND=KAFKA_STATIC_URL
        else:
            URL_TO_SEND=KAFKA_URL
        return make_response(jsonify(KAFKA_ENDPOINT=URL_TO_SEND), 200)
    except HTTPError as e:
        app.logger.error(f'HTTP error occurred: {e.response.url} - {e.response.status_code} - {e.response.text}')
        return make_response(e.response.text, e.response.status_code)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 500)
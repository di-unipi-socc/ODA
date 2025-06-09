from flask import Flask, request, make_response, jsonify
from datetime import datetime
import influxdb_client, logging, sys, os, gzip, json, uuid
from influxdb_client.client.write_api import SYNCHRONOUS

#CONFIGURATION
DB_PORT= os.environ["DB_PORT"]
bucket = os.environ["DOCKER_INFLUXDB_INIT_BUCKET"]
org = os.environ["DOCKER_INFLUXDB_INIT_ORG"]
token = os.environ["DOCKER_INFLUXDB_INIT_ADMIN_TOKEN"]
url="http://influxdb:"+DB_PORT

app = Flask(__name__)
client = influxdb_client.InfluxDBClient(url=url,token=token,org=org)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

#WRITE IN DB
'''
The payload must be a JSON with the following structure:
{
    "timestamp": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ,
    "generator_id": string
    "topic": string
    "data": str
'''
@app.route("/writeDB", methods=["POST"])
def write():
    try:
        msg = request.get_json()
        writeDB(msg)
        return make_response("Data written to InfluxDB", 200)
    except Exception as e:
        if msg:
            app.logger.error('Error writing to DB with message: %s', msg)
        app.logger.error(repr(e))
        return make_response(repr(e), 400)

#Takes the payload and write it to the InfluxDB
def writeDB(msg):
    timestamp = msg["timestamp"]
    generator_id = msg["generator_id"]
    topic = msg["topic"]
    data = msg["data"]
    
    try:
        # Try to parse with milliseconds
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        # If that fails, try parsing without milliseconds
        dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
    
    unixtimestamp = int(dt.timestamp())
    id = str(uuid.uuid4())

    write_api = client.write_api(write_options=SYNCHRONOUS)
    p = influxdb_client.Point("misure").time(unixtimestamp,"s").tag("topic", topic).tag("generator_id",generator_id).tag("id",id).field("data", data)
    write_api.write(bucket=bucket, org=org, record=p)


#QUERY DB
'''
The payload for a query must be a JSON having at least one of the following fields:
"start": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ
"stop": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ
"topic": string
"generator_id": string

The response is an unsorted JSON array with all the records that match the query.
'''
@app.route("/query", methods=["POST"]) 
def query():
    try:
        msg = request.get_json()
        if not msg:
            return make_response("Empty query", 404)
        start = msg.get("start",None)
        stop = msg.get("stop",None)
        topic = msg.get("topic",None)
        generator_id = msg.get("generator_id",None)

        app.logger.info('Querying db with parameters: start=%s, stop=%s, topic=%s, generator_id=%s', start,stop,topic,generator_id)

        query = f'from(bucket:"{bucket}")'
        
        query = buildQuery(query,start,stop,topic,generator_id)

        app.logger.info('Query: %s', query)

        result = client.query_api().query(org=org, query=query)
        
        if not result:
            return make_response("", 404)
        result = extractResults(result)

        content = gzip.compress(json.dumps(result).encode('utf8'),mtime=0)
        response = make_response(content)
        response.headers['Content-length'] = len(content)
        response.headers['Content-Encoding'] = 'gzip'
        return response
        #return make_response(jsonify(result), 200)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 400)
    
#Builds the DB query string based on the HTTP query parameters
def buildQuery(query,start,stop,topic,generator_id):
    if start:
        start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        start = "-10"
    if stop:
        stop = datetime.strptime(stop, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        stop = datetime.strftime(datetime.now(),"%Y-%m-%dT%H:%M:%S.000Z")
    range = f'range(start: {start}, stop: {stop})'

    query += f"|> {range}"
    if topic:
        topic = f'filter(fn:(r) => r["topic"] == "{topic}")'
        query += f"|> {topic}"

    if generator_id:
        generator_id = f'filter(fn:(r) => r["generator_id"] == "{generator_id}")'
        query += f"|> {generator_id}"
    return query

#Takes the query result and create a list of records for the response
def extractResults(result):
    results = []
    for table in result:
        for record in table.records:
            time = record.get_time().strftime("%Y-%m-%dT%H:%M:%SZ")
            results.append({"timestamp":time,"data":record.get_value(),"topic":record.values["topic"],"generator_id":record.values["generator_id"]})
    return results

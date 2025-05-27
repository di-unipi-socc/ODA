from flask import Flask, request, make_response, jsonify
import logging, sys, os, requests, json, gzip, statistics
from requests.exceptions import HTTPError
from datetime import datetime, timedelta, timezone
from collections import defaultdict

#CONFIGURATION
DB_MANAGER_PORT= os.environ["DB_MANAGER_PORT"]
DB_MANAGER_URL = "http://dbmanager:"+DB_MANAGER_PORT

app = Flask(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# Supported aggregation functions
agg_functions = {
    "sum": sum,
    "avg": statistics.mean,
    "min": min,
    "max": max
}

#AGGREGATOR SERVICE
@app.route("/query", methods=["POST"]) 
def query():
    try:
        msg = request.get_json()
        if not msg or "aggregator" not in msg:
            return make_response("Empty query", 404)
        
        fun = msg["aggregator"].get("fun", None)
        field = msg["aggregator"].get("field", None)
        unit = msg["aggregator"].get("unit", None)
        if fun is None:
            return make_response('Missing aggregation function "fun"', 400)
        if field is None:
            return make_response('Missing aggregation field "field"', 400)
        if unit is None:
            return make_response('Missing aggregation unit "unit"', 400)
        
        if fun not in agg_functions:
            raise make_response(f"Unsupported aggregation function: {fun}", 400)
        

        URL= DB_MANAGER_URL + '/query?unzip=true'
        app.logger.info(f"Sending query to {URL}")
        app.logger.info(f"Query: {msg}")
        x = requests.post(URL, json=msg, stream=True)
        x.raise_for_status()
        logging.info("Query sent")
        result = x.json()
        if not result:
            return make_response("No data found", 404)
        aggr = create_aggregated_result(msg, result)
        app.logger.info('Compressing response')
        content = gzip.compress(json.dumps(aggr).encode('utf8'),mtime=0)
        response = make_response(content)
        response.headers['Content-length'] = len(content)
        response.headers['Content-Encoding'] = 'gzip'       
        return response
    except HTTPError as e:
        app.logger.error(f'HTTP error occurred: {e.response.url} - {e.response.status_code} - {e.response.text}')
        return make_response(e.response.text, e.response.status_code)
    except Exception as e:
        app.logger.error(repr(e))
        return make_response(repr(e), 500)
    
#Aggregates the data based on the aggregation function
def create_aggregated_result(msg, result):
    start = msg.get("start", None)
    stop = msg.get("stop", None)
    topic = msg.get("topic", None)
    generator_id = msg.get("generator_id", None)
    fun = msg["aggregator"].get("fun", None)
    field = msg["aggregator"].get("field", None)
    target_unit = msg["aggregator"].get("unit", None)
    frequency = msg["aggregator"].get("frequency", None)
    

    if len(result) == 1:
        return result
   
    def get_data_dict(data_field):
        if isinstance(data_field, dict):
            return data_field
        elif isinstance(data_field, str):
            data_field = data_field.replace("'", "\"")
            try:
                return json.loads(data_field)
            except Exception:
                return {}
        return {}

    # If start and stop are not provided, use the first and last data timestamps
    if not start or not stop:
        timestamps = [datetime.strptime(item['timestamp'], "%Y-%m-%dT%H:%M:%SZ") for item in result]
        if not start:
            start = min(timestamps).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not stop:
            stop = max(timestamps).strftime("%Y-%m-%dT%H:%M:%SZ")

    app.logger.info(f"Aggregating data with parameters: start={start}, stop={stop}, topic={topic}, generator_id={generator_id}, fun={fun}, field={field}, target_unit={target_unit}, frequency={frequency}")

    agg_fun = agg_functions[fun]
    
    # Extract values matching criteria
    def extract_values(items):
        values = []
        for item in items:    
            data_field = item.get("data")
            data = get_data_dict(data_field)
            if not data or field not in data:
                # Skip if data if empty or does not contain the field
                continue
            attr = data.get(field, {})
            if not attr:
                # Skip if data if does not contain the field
                continue
            val = attr.get("value")
            unit = attr.get("unit")
            conv_val = convert(val, unit, target_unit)
            if conv_val is not None:
                values.append(conv_val)
            # if value is not of the target unit and cannot be converted, skip it
        return values

    # Case 1: No frequency
    if frequency is None:
        app.logger.info("No frequency provided, aggregating all data")
        values = extract_values(result)
        if not values:
            return {}
        return {
            "timestamp": stop,
            "generator_id": generator_id,
            "topic": topic,
            "data": str({
                field: {
                    "unit": target_unit,
                    "value": float(agg_fun(values))
                }
            })
        }

    # Case 2: With frequency
    app.logger.info(f"Aggregating data with frequency: {frequency} minutes")
    start_dt = parse_timestamp(start)
    stop_dt = parse_timestamp(stop)
    frequency_td = timedelta(minutes=frequency)
    buckets = defaultdict(list)

    # Create buckets based on frequency
    for item in result:
        try:
            ts = parse_timestamp(item["timestamp"])
        #should not happen, but just in case
        except Exception:
            continue
        if start_dt <= ts <= stop_dt:
            window_index = (ts - start_dt) // frequency_td
            bucket_end = start_dt + (window_index + 1) * frequency_td
            if bucket_end > stop_dt:
                bucket_end = stop_dt
            buckets[bucket_end].append(item)

    app.logger.info(f"Number of buckets created: {len(buckets)}")
    # Aggregate values in each bucket
    aggregated = []
    for bucket_end in sorted(buckets.keys()):
        values = extract_values(buckets[bucket_end])
        if values:
            aggregated.append({
                "timestamp": bucket_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "generator_id": generator_id,
                "topic": topic,
                "data": str({
                    field: {
                        "unit": target_unit,
                        "value": float(agg_fun(values))
                    }
                })
            })

    return aggregated

# Parse timestamps with 'Z' as UTC
def parse_timestamp(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def convert(value, from_unit, to_unit):
    if from_unit == to_unit:
        return value

    # Bidirectional conversion rules
    conversions = {
        ("W", "kW"): lambda v: v / 1000,
        ("kW", "W"): lambda v: v * 1000,
        ("Wh", "kWh"): lambda v: v / 1000,
        ("kWh", "Wh"): lambda v: v * 1000,
        ("A", "mA"): lambda v: v * 1000,
        ("mA", "A"): lambda v: v / 1000,
        ("Celsius", "Kelvin"): lambda v: v + 273.15,
        ("Kelvin", "Celsius"): lambda v: v - 273.15,
    }

    func = conversions.get((from_unit, to_unit))
    if func:
        try:
            return func(value)
        except Exception:
            return None  # skip if non-numeric or invalid
    return None  # no conversion path
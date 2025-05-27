# ODA - Observable Data Access

Observable Data Access service developed within NEST Project, Task 8.6.2.

## Overview

![ODA Architecture](docs/ODA.png)

The Observable Data Access (ODA) service is a microservice-based architecture that allows Data Generators to send data to the service and Data Consumers to query the data stored in the service. The service is composed of the following microservices:

1. API Gateway: the entry point of the service. It provides the Kafka endpoint to Data Generators and Data Consumers and manages the registration of the topics. It also provides the query endpoint to Data Consumers.
2. Database Manager: the microservice that manages the InfluxDB database. It stores the data sent by the Data Generators and provides the data to the Data Consumers.
3. InfluxDB: the time-series database that stores the data sent by the Data Generators.
4. Kafka: the message broker - managed by Zookeeper - that allows Data Generators to stream data through ODA and Data Consumers to receive streamed data through ODA.
5. Data Pump: the microservice that subscribes to the Kafka topics and sends the data to be stored to the Database Manager.
6. Topic Manager: the microservice that manages the Kafka topics registered in ODA.
7. Data Aggregator: the microservice that manages the aggregation of the data stored in ODA. It allows querying the data stored in ODA and receiving aggregated results.

The [detailed overview](/docs/ODA.pdf) is available in the `docs` folder.

## Prerequisites

* ODA is versioned using [Git](https://git-scm.com/). To clone the repository, you need to have Git installed on the target machine.
* ODA is shipped using [Docker](https://www.docker.com/) and deployed using [Docker Compose](https://docs.docker.com/compose/). To run the service, you need Docker and Docker Compose installed and running on the target machine.

## Quick start

To run the ODA service with default configuration, follow these steps:

1. Clone the repository:

```git clone https://github.com/di-unipi-socc/ODA.git```

2. Navigate to the repository:

```cd ODA```

3. Build and Run ODA:

```./start.sh```

To stop ODA execute:

```./stop.sh```

To remove ODA execute:

```./clean.sh```    to remove the Docker images and the Docker network.
```./clean.sh -v``` to remove the Docker images, the Docker network and the db volumes (deleting all db data).

To update ODA (when this repo is updated):

    1. Stop ODA with `./stop.sh`.
    2. Remove the Docker images and the Docker network with `./clean.sh`.
    3. Pull the new version of the repository with `git pull`.
    4. Start ODA with `./start.sh`.

## API

Data Generators and Data Consumers can obtain the Kafka endpoint from the API Gateway.
The API of the API Gateway is documented using [Swagger](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/alebocci/ODA/main/docs/ODAopenapi.yaml).

Data Generators must send the list of topics they want to produce to the API Gateway. Data Consumers will obtain the list of available topics from the API Gateway.

To send or receive streamed data, Data Generators and Data Consumers must use the Kafka endpoint provided by the API Gateway and a Kafka client following the [Kafka documentation](https://docs.confluent.io/kafka-client/overview.html). We provide two Python examples in the [client_examples folder](/client_examples).

The data format of the data streamed or stored in ODA is JSON. The messages must include the following fields:

```
    "timestamp": string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ (note: timestamps in ODA are in UTC time),
    "generator_id": a string representing the ID of the generator,
    "topic": a string representing the topic where the message will be sent,
    "data": a string representing the data of the message.
```

The common used data format for the `data` field is the one proposed by POLIMI, please refer to the [POLIMI data format documentation](docs/ODA_UpTown_DataFormat.pdf) for more details.

## Queries

To query the data stored in ODA, Data Consumers must send a HTTP POST to the API Gateway at `http://<host>:50005/query`. The paload must be a JSON file including at least one of the following fields:

```
    "generator_id": string representing the ID of the generator,
    "topic": a string representing the topic of the data requested,
    "start": a string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ representing the time window start of the query,
    "stop": a string formatted in ISO 8601 YYYY:MM:DDTHH:MM:SSZ representing the time window end of the query.
```

The response will contain an archive ```.gzip``` containing the JSON representing the requested data.

### Example

Using the utility `curl` to send a query to the API Gateway (running on `host` at port `50005`):

```
curl -X POST http://host:50005/query  -H 'Content-Type: application/json' -d '{"topic":"generic_topic"}' --output results.gzip
```

The query will return the data stored in the ODA database with the topic `generic_topic` in a file named `results.gzip` containing a JSON file having the ODA data format. (NOTE: if the query does not return any data, the file will be empty and the HTTP response code will be 404).

### Aggregated Queries

It is possible to query the data stored in ODA and receive aggregated results by adding the `aggregator` field to your query JSON payload. The `aggregator` field must be an object specifying the aggregation parameters:

```
"aggregator": {
    "fun": "sum" | "avg" | "min" | "max",   // Aggregation function (required)
    "field": "<field_name>",                   // Name of the field to aggregate (required)
    "unit": "<unit>"                           // Target unit for the result (required)
    "frequency": <minutes>                      // (Optional) Aggregate in time buckets of this size (in minutes)
}
```

- `fun`: Aggregation function. Supported values are `sum`, `avg`, `min`, `max`.
- `field`: The name of the field inside the `data` object to aggregate (e.g., `power`, `temperature`).
- `unit`: The unit you want the result in (e.g., `W`, `kW`, `Celsius`, `Kelvin`).
- `frequency`: (Optional) If provided, the aggregation will be performed in time buckets of the given size (in minutes). If omitted, aggregation is performed over the entire result set.

##### Supported Unit Conversions

The aggregator supports automatic conversion between the following units:

- Power: `W` (Watt) ↔ `kW` (Kilowatt)
- Energy: `Wh` (Watt-hour) ↔ `kWh` (Kilowatt-hour)
- Current: `A` (Ampere) ↔ `mA` (Milliampere)
- Temperature: `Celsius` ↔ `Kelvin`

Specify the desired target unit in the `unit` field. The service will convert values as needed before aggregation.

#### Example: Aggregated Query (Total Power in kW)

```
curl -X POST http://host:50005/query  -H 'Content-Type: application/json' -d '{
    "topic": "generic_topic",
    "aggregator": {
        "fun": "sum",
        "field": "power",
        "unit": "kW"
    }
}' --output results.gzip
```

The response will be a `.gzip` archive containing a JSON file with the aggregated results for the topic `generic_topic`, with the `sum` of all the `power` fields and converting them in `kW`. For example:

```json
{
    "timestamp": "2024-10-01T12:00:00Z",
    "generator_id": null,
    "topic": "generic_topic",
    "data": {
        "power": 5.0, \\ Sum of all power values in kW
        "unit": "kW"
    }
}
```


#### Example: Aggregated Query with Frequency (Average Temperature per 60 Minutes)

```
curl -X POST http://host:50005/query  -H 'Content-Type: application/json' -d '{
    "topic": "generic_topic",
    "aggregator": {
        "fun": "avg",
        "field": "temperature",
        "unit": "Celsius",
        "frequency": 60
    }
}' --output results.gzip
```

The response will be a `.gzip` archive containing a JSON file with aggregated results for the topic `generic_topic`. Each entry in the JSON represents a `60`-minute time window and includes the `average` of all `temperature` readings within that window. Temperatures are converted to `Celsius` before averaging. The timestamp for each object corresponds to the end of the respective 60-minute window. Windows without data will not be included in the response.
For example, considering three windows:

```json
{
    "timestamp": "2024-10-01T12:00:00Z",
    "generator_id": null,
    "topic": "generic_topic",
    "data": {
        "temperature": 22.5, \\ Average temperature in Celsius of first 60 minutes
        "unit": "Celsius"
    }
},
{
    "timestamp": "2024-10-01T13:00:00Z",
    "generator_id": null,
    "topic": "generic_topic",
    "data": {
        "temperature": 23.0, \\ Average temperature in Celsius of second 60 minutes
        "unit": "Celsius"
    }
},
{
    "timestamp": "2024-10-01T14:00:00Z",
    "generator_id": null,
    "topic": "generic_topic",
    "data": {
        "temperature": 21.8, \\ Average temperature in Celsius of third 60 minutes
        "unit": "Celsius"
    }
}

```

## Configuration

The ODA service can be configured in two aspects:

1. The ports of every microservice composing ODA and the Kafka endpoint.

This configuration is achieved through environment variables, which are defined in the `.env` file located at the root directory of the repository. The `.env` file should include the following environment variables:

    - api_gateway_port: the port where the API Gateway will be listening.
    - kafka_port: the port where the Kafka broker will be listening for an outside connection.
    - kafka_address: the address of the Kafka broker.
    - db_port: the port where the InfluxDB will be listening.
    - db_manager_port: the port where the database manager will be listening.
    - kafka_internal_port: the port where the Kafka broker will be listening for internal connection.
    - k_admin_port: the port where the Kafka Admin will be listening.
    - query_aggregator_port: the port where the Query Aggregator will be listening.

Only the ```api_gateway_port```, ```kafka_port``` and  the```kafka_address``` are reachable from outside ODA. The other ports are only reachable from inside the Docker network.
By default, we provide development configuration values (see ```.env``` file) to run ODA in localhost.

2. The InfluxDB database configuration.

This configuration is achieved through environment variables, which are defined in the `influx.env` file located at the root directory of the repository. Follow [InfluxDB documentation](https://docs.influxdata.com/influxdb/v1/administration/config/) to configure the database. By default, we provide development configuration values not considered safe for production (see ```influx.env``` file).

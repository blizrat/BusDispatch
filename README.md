# Bus Dispatch System

## Project Overview
Public transportation systems often struggle with uneven demand across bus stops, leading to overcrowding and inefficient resource allocation. This project aims to solve that by automatically dispatching extra buses when the crowd at a bus stand exceeds the regular bus capacity.

It uses face detection (YOLO/OpenCV) to count people at stops, a Kafka-based real-time data pipeline, and KSQLDB to process and analyze the incoming data. The system also features peak hour prediction using time series models and a live dashboard to visualize bus demand and dispatches in real-time.

## Tech Stack Used
Kafka + Kafka Connect + Schema Registry

KSQLDB for real-time querying

Flask for live dashboard

PostgreSQL for storing processed data

Docker + Docker Compose for deployment

Python (Avro Producer & Dashboard Backend)

## Setup Instructions

1. Install all the required packages and Python dependencies:

  ```
pip install -r requirements.txt
```

2. Bring the Docker compose up and make sure everything is up and running

```
docker-compose up -d
docker-compose ps
```

3. Run the producer file to generate (if not fetched from IOT devices) and stream data into kafka topic

```
python producer.py
```
4. Run the following JDBC Sink connector command in a new terminal to stream your Kafka topic into Postgres Database
```
  curl -X PUT http://localhost:8083/connectors/sink-jdbc-postgres-01/config \
     -H "Content-Type: application/json" -d '{
    "connector.class"                    : "io.confluent.connect.jdbc.JdbcSinkConnector",
    "connection.url"                     : "jdbc:postgresql://postgres:5432/postgres",
    "topics"                             : "BUS_STREAM_ENRICHED",
    "key.converter"                      : "org.apache.kafka.connect.storage.StringConverter",
    "value.converter"                    : "io.confluent.connect.avro.AvroConverter",
    "value.converter.schema.registry.url": "http://schema-registry:8081",
    "connection.user"                    : "postgres",
    "connection.password"                : "postgres",
    "auto.create"                        : true,
    "auto.evolve"                        : true,
    "insert.mode"                        : "insert",
    "pk.mode"                            : "record_value"
}'
```
5. Run the following command in a new terminal to go to your KSQL DB interface

```
docker exec -it ksqldb ksql http://ksqldb:8088
```

6. Run the following queries to set up/create new topics for dashboard and
   Set the offset to earliest to fetch data from the start
   
  ```
  SET 'auto.offset.reset' = 'earliest';
  ```

  Query to create a Kafka stream on top of BUS_TOPIC_AVRO topic
   
  ```
  CREATE STREAM bus_stream (bus_stop_id INT,
                    people_count INT,
                    temperature DOUBLE,
                    weather VARCHAR,
                    timestamp VARCHAR)
              WITH (KAFKA_TOPIC='bus_topic_avro',
                    VALUE_FORMAT='AVRO');
  ```

  Query to extract useful information and to calculate the additional bus required logic
  
  ```
  CREATE STREAM bus_stream_enriched WITH (FORMAT='AVRO') AS
  SELECT 
      bus_stop_id,
      people_count,
      temperature,
      weather,
      timestamp,
  
      -- Extract and cast as integers
      CAST(SUBSTRING(timestamp, 6, 2) AS INTEGER) AS month,
      CAST(SUBSTRING(timestamp, 9, 2) AS INTEGER) AS day,
      CAST(SUBSTRING(timestamp, 12, 2) AS INTEGER) AS hour,
      CAST(SUBSTRING(timestamp, 15, 2) AS INTEGER) AS minute,
  
      CASE 
          WHEN people_count > 15 THEN 1 
          ELSE 0 
      END AS send_extra_bus
  FROM bus_stream;
  ```

  Queries to create topics, streams and tables to transform bus_stream_enriched data for live dashboard

  ```
-- Stream to fetch current day data
  CREATE STREAM bus_stream_today WITH (
  KAFKA_TOPIC='bus_stream_today',
  PARTITIONS=1,
  REPLICAS=1,
  VALUE_FORMAT='AVRO'
  ) AS 
  SELECT *
  FROM bus_stream_enriched
  WHERE SUBSTRING(timestamp, 1, 10) = 'write current date here'
  EMIT CHANGES;



-- Table for LiveStreamDashBoard

CREATE TABLE LIVE_DASHBOARD_STREAM WITH (
    KAFKA_TOPIC='LIVE_DASHBOARD_STREAM',
    PARTITIONS=1,
    REPLICAS=1
) AS 
SELECT 
  'today' AS key,
  SUM(SEND_EXTRA_BUS) AS TOTAL_EXTRA_BUSES_SENT,
  AVG(TEMPERATURE) AS AVG_TEMPERATURE,
  AVG(PEOPLE_COUNT) AS AVG_PEOPLE_COUNT
FROM BUS_STREAM_TODAY
GROUP BY 'today';

-- Table to fetch Busiest bus stop
CREATE TABLE MAXI_BUS_STOP WITH (
    KAFKA_TOPIC='MAX_STOP',
    PARTITIONS=1,
    REPLICAS=1
) AS 
SELECT 
  bus_stop_id,
  SUM(people_count) as people_count
FROM BUS_STREAM_TODAY
GROUP BY bus_stop_id;

```

7. Run app.py to stream your live dashboard onto localhost//127.0.0.1:8080

```
python app.py
```
   


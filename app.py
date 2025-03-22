# app.py
from flask import Flask, render_template, jsonify
from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
import threading
import time
import json

app = Flask(__name__)
latest_message = {}

# Kafka + Schema Registry config
consumer_config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'dashboard-group',
    'auto.offset.reset': 'latest'
}

schema_registry_conf = {
    'url': 'http://localhost:8081'
}

topic = "LIVE_DASHBOARD_STREAM"

def kafka_consumer_thread():
    global latest_message
    schema_registry_client = SchemaRegistryClient(schema_registry_conf)

    # Get the latest value schema from Schema Registry
    latest_version = schema_registry_client.get_latest_version(topic + '-value')
    schema_str = latest_version.schema.schema_str

    avro_deserializer = AvroDeserializer(
        schema_registry_client=schema_registry_client,
        schema_str=schema_str
    )

    consumer = Consumer(consumer_config)
    consumer.subscribe([topic])

    print("🚌 Kafka consumer started...")

    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue

        value = avro_deserializer(msg.value(), SerializationContext(topic, MessageField.VALUE))
        if value:
            latest_message = value

# Start Kafka consumer in a background thread
threading.Thread(target=kafka_consumer_thread, daemon=True).start()

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/data")
def data():
    return jsonify(latest_message)

if __name__ == "__main__":
    app.run(debug=True)

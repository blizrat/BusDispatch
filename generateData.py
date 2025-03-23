import time
import random
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

# Load schema from file
with open("bus_data.avsc", "r") as f:
    schema_str = f.read()

# Create Schema Registry client
schema_registry_conf = {'url': 'http://localhost:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

# Define how to convert dict to schema-compatible format
def dict_to_busdata(obj, ctx):
    return obj

# Create AvroSerializer
avro_serializer = AvroSerializer(schema_registry_client, schema_str, dict_to_busdata)

# Kafka Producer config
producer_conf = {
    'bootstrap.servers': 'localhost:9092',
    'key.serializer': StringSerializer('utf_8'),
    'value.serializer': avro_serializer
}

producer = SerializingProducer(producer_conf)

# Topic name
topic = "bus_topic_avro"

# Simulate event data
def generate_event():
    return {
        "bus_stop_id": random.randint(1, 5),
        "people_count": random.randint(5, 30),
        "temperature": round(random.uniform(22.0, 38.0), 2),
        "weather": random.choice(["Sunny", "Cloudy", "Rainy"]),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }

# Callback for delivery
def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Delivery failed: {err}")
    else:
        print(f"✅ Sent to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

print("🚀 Producing data to 'bus_stream_raw'... Press Ctrl+C to stop.")

try:
    while True:
        data = generate_event()
        producer.produce(topic=topic, key=str(data["bus_stop_id"]), value=data, on_delivery=delivery_report)
        producer.flush()
        time.sleep(1)
except KeyboardInterrupt:
    print("🛑 Stopped producing.")

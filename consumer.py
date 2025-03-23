from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

def dict_to_record(obj, ctx):
    return obj

# Kafka & Schema Registry config
schema_registry_conf = {
    'url': 'http://localhost:8081'
}
kafka_conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'live_dashboard_consumer',
    'auto.offset.reset': 'earliest'
}

# Set up schema registry client and deserializer
schema_registry_client = SchemaRegistryClient(schema_registry_conf)
avro_deserializer = AvroDeserializer(
    schema_registry_client=schema_registry_client,
    schema_str=None,  # auto-fetch schema from Schema Registry
    from_dict=dict_to_record
)

# Create Kafka consumer
consumer = Consumer(kafka_conf)
consumer.subscribe(['LIVE_DASHBOARD_STREAM'])

print("🔄 Listening for messages on topic: LIVE_DASHBOARD_STREAM\n")

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue

        key = msg.key().decode('utf-8') if msg.key() else 'NULL'
        value = avro_deserializer(msg.value(), SerializationContext(msg.topic(), MessageField.VALUE))

        if value:
            print(f"KEY: {key}")
            print(f"  TOTAL_EXTRA_BUSES_SENT: {value['TOTAL_EXTRA_BUSES_SENT']}")
            print(f"  AVG_TEMPERATURE:        {value['AVG_TEMPERATURE']}")
            print(f"  AVG_PEOPLE_COUNT:       {value['AVG_PEOPLE_COUNT']}\n")

except KeyboardInterrupt:
    print("\n🛑 Stopped by user")

finally:
    consumer.close()

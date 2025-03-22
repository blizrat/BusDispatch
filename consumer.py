from confluent_kafka.avro import AvroConsumer
import sys

# Kafka + Schema Registry configuration
consumer_config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'bus-consumer-group',
    'schema.registry.url': 'http://localhost:8081',
    'auto.offset.reset': 'earliest'
}

# Create the AvroConsumer instance
consumer = AvroConsumer(consumer_config)

# Subscribe to your topic
consumer.subscribe(['LIVE_DASHBOARD_STREAM'])

print("🚌 Consuming messages from 'bus-topic'... Press Ctrl+C to stop.\n")

try:
    while True:
        msg = consumer.poll(1.0)  # timeout in seconds
        if msg is None:
            continue
        if msg.error():
            print(f"⚠️ Error: {msg.error()}")
        else:
            value = msg.value()
            print(f"✅ Received: {value}")
except KeyboardInterrupt:
    print("\n🛑 Stopping consumer...")
finally:
    consumer.close()

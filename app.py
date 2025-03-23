from flask import Flask, render_template, jsonify
from confluent_kafka.avro import AvroConsumer
from confluent_kafka.avro.serializer import SerializerError
import json
import threading
import time

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# Kafka consumer configuration
kafka_config = {
    'bootstrap.servers': 'localhost:9092',  # Update with your Kafka broker address
    'schema.registry.url': 'http://localhost:8081',  # Update with your Schema Registry URL
    'group.id': 'dashboard-web-consumer',
    'auto.offset.reset': 'latest'  # Start consuming from the latest messages
}

# Global variable to store the latest data
latest_data = {
    'key': 'today',
    'total_extra_buses_sent': 0,
    'avg_temperature': 0.0,
    'avg_people_count': 0.0,
    'timestamp': time.time(),
    'busiest_stop': {
        'bus_stop_id': None,
        'people_count': 0
    },
    'history': {
        'timestamps': [],
        'buses': [],
        'temperatures': [],
        'people_counts': []
    }
}

# Flag to control the Kafka consumer threads
running = True


@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    """API endpoint to get the latest data"""
    return jsonify(latest_data)


def dashboard_stream_consumer():
    """Background thread function for consuming LIVE_DASHBOARD_STREAM messages"""
    global latest_data, running

    # Create Avro Consumer
    consumer = AvroConsumer(kafka_config)

    # Subscribe to the LIVE_DASHBOARD_STREAM topic
    consumer.subscribe(['LIVE_DASHBOARD_STREAM'])

    # For keeping track of history (limited to last 20 points)
    MAX_HISTORY_POINTS = 20

    try:
        while running:
            # Poll for messages
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                print(f"Dashboard stream consumer error: {msg.error()}")
                continue

            # Extract data from the Avro message
            try:
                key = msg.key() if msg.key() else "None"
                value = msg.value()

                current_time = time.strftime("%H:%M:%S")
                buses = value.get('TOTAL_EXTRA_BUSES_SENT', 0)
                temp = value.get('AVG_TEMPERATURE', 0.0)
                people = value.get('AVG_PEOPLE_COUNT', 0.0)

                # Update the latest data
                latest_data.update({
                    'key': key,
                    'total_extra_buses_sent': buses,
                    'avg_temperature': temp,
                    'avg_people_count': people,
                    'timestamp': time.time()
                })

                # Update history
                latest_data['history']['timestamps'].append(current_time)
                latest_data['history']['buses'].append(buses)
                latest_data['history']['temperatures'].append(temp)
                latest_data['history']['people_counts'].append(people)

                # Limit history length
                if len(latest_data['history']['timestamps']) > MAX_HISTORY_POINTS:
                    latest_data['history']['timestamps'] = latest_data['history']['timestamps'][-MAX_HISTORY_POINTS:]
                    latest_data['history']['buses'] = latest_data['history']['buses'][-MAX_HISTORY_POINTS:]
                    latest_data['history']['temperatures'] = latest_data['history']['temperatures'][
                                                             -MAX_HISTORY_POINTS:]
                    latest_data['history']['people_counts'] = latest_data['history']['people_counts'][
                                                              -MAX_HISTORY_POINTS:]

            except SerializerError as e:
                print(f"Message deserialization failed: {e}")

    except Exception as e:
        print(f"Dashboard stream consumer thread error: {e}")
    finally:
        # Close the consumer
        consumer.close()
        print("Dashboard stream consumer closed.")


def max_bus_stop_consumer():
    """Background thread function for consuming MAX_STOP messages"""
    global latest_data, running

    # Create an AvroConsumer for the MAX_STOP topic
    max_stop_config = kafka_config.copy()
    max_stop_config['group.id'] = 'max-bus-stop-consumer'

    consumer = AvroConsumer(max_stop_config)
    consumer.subscribe(['MAX_STOP'])

    # Keep track of all bus stops and their people counts
    bus_stops = {}

    try:
        while running:
            # Poll for messages
            msg = consumer.poll(timeout=1.0)

            if msg is None:
                continue

            if msg.error():
                print(f"Max bus stop consumer error: {msg.error()}")
                continue

            # Process the message
            try:
                # Get the key and value
                key = msg.key()
                value = msg.value()

                print(f"MAX_STOP message - Key: {key}, Value: {value}")

                # Extract bus_stop_id (could be in key or value)
                bus_stop_id = None

                # If key is a dictionary, try to get BUS_STOP_ID from it
                if key is not None and hasattr(key, 'get'):
                    bus_stop_id = key.get('BUS_STOP_ID')
                # If key is a primitive value (like an integer), use it directly
                elif key is not None:
                    bus_stop_id = key

                # If still None, try to get from value
                if bus_stop_id is None and value is not None and hasattr(value, 'get'):
                    bus_stop_id = value.get('BUS_STOP_ID')

                # Extract people_count from value
                people_count = 0
                if value is not None and hasattr(value, 'get'):
                    people_count = value.get('PEOPLE_COUNT', 0)

                # Convert to appropriate types
                if bus_stop_id is not None:
                    bus_stop_id = str(bus_stop_id)
                if people_count is not None:
                    people_count = int(people_count)
                else:
                    people_count = 0

                print(f"Parsed data: bus_stop_id={bus_stop_id}, people_count={people_count}")

                # Update our local dictionary of all bus stops
                if bus_stop_id is not None:
                    bus_stops[bus_stop_id] = people_count

                    # Find the busiest stop from all known stops
                    busiest_id = max(bus_stops, key=bus_stops.get, default=None)
                    busiest_count = bus_stops.get(busiest_id, 0)

                    # Update the latest_data if this is indeed the busiest stop
                    if busiest_id is not None and busiest_count > latest_data['busiest_stop']['people_count']:
                        latest_data['busiest_stop'] = {
                            'bus_stop_id': busiest_id,
                            'people_count': busiest_count
                        }
                        print(f"New busiest stop: {busiest_id} with {busiest_count} people")

            except SerializerError as e:
                print(f"Message deserialization failed: {e}")
            except Exception as e:
                print(f"Error processing MAX_STOP message: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"Max bus stop consumer thread error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        consumer.close()
        print("Max bus stop consumer closed.")

if __name__ == '__main__':
    # Start the Kafka consumers in background threads
    dashboard_thread = threading.Thread(target=dashboard_stream_consumer)
    dashboard_thread.daemon = True
    dashboard_thread.start()

    max_stop_thread = threading.Thread(target=max_bus_stop_consumer)
    max_stop_thread.daemon = True
    max_stop_thread.start()

    try:
        # Start the Flask app on port 8080 instead of the default 5000
        app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
    finally:
        # Set the flag to stop the consumer threads
        running = False
        # Wait for the consumer threads to finish
        dashboard_thread.join(timeout=5.0)
        max_stop_thread.join(timeout=5.0)
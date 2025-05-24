# kafka_streaming/producer.py

from kafka import KafkaProducer
import json, time, os

# Read Kafka broker from env (set in docker-compose)
BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

producer = KafkaProducer(
    bootstrap_servers=BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

# Load all lines from your new test_sample.jsonl
with open('data_1.jsonl', 'r') as f:
    reviews = []
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            reviews.append(json.loads(line))
        except json.JSONDecodeError:
            # skip invalid JSON
            continue

# Stream every review
for review in reviews:
    producer.send('amazon-reviews', review)
    print("Sent:", review.get('reviewText', '')[:60].replace("\n"," "))
    time.sleep(1)    # adjust or remove delay as needed

producer.flush()
print("All reviews streamed.")

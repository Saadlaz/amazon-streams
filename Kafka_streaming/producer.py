from kafka import KafkaProducer
import json, time, os

BROKER = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
producer = KafkaProducer(
    bootstrap_servers=BROKER,
    value_serializer=lambda v: json.dumps(v).encode()
)

with open('Data.jsonl','r') as f:
    reviews = [json.loads(l) for l in f if l.strip()]

for r in reviews[:100]:
    producer.send('amazon-reviews', r)
    print("Sent:", r.get('reviewText','')[:60])
    time.sleep(1)

producer.flush()

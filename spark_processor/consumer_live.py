# spark_processor/consumer_live.py

from datetime import datetime
import requests
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import from_json, col, rand
from pyspark.sql.types import StructType, StringType

# HTTP endpoint in Django to relay live events
DJANGO_RELAY_URL = "http://dashboard:8000/reviews/api/push_live/"

def push_live(review, sentiment, ts):
    payload = {
        "review": review,
        "sentiment": sentiment,
        "timestamp": ts.isoformat()
    }
    # fire-and-forget
    requests.post(DJANGO_RELAY_URL, json=payload, timeout=1)

if __name__ == "__main__":
    spark = SparkSession.builder.appName("LiveOnly").getOrCreate()

    # 1) Load ML pipeline
    model = PipelineModel.load("/app/rf_pipeline_amazon_json")
    labels = next(s.labels for s in model.stages if hasattr(s, "labels"))

    # 2) Read from Kafka
    kafka = (
        spark.readStream
             .format("kafka")
             .option("kafka.bootstrap.servers", "kafka:9092")
             .option("subscribe", "amazon-reviews")
             .option("startingOffsets", "earliest")
             .load()
    )

    # 3) Parse JSON
    schema = StructType().add("reviewText", StringType())
    reviews = (
        kafka
          .selectExpr("CAST(value AS STRING) AS json_str")
          .select(from_json(col("json_str"), schema).alias("data"))
          .select("data.reviewText")
    )

    # 4) Classify
    preds = model.transform(reviews).select("reviewText", "prediction")

    # 5) Relay each batch over HTTP
    def foreach_batch(df, epoch_id):
        for row in df.collect():
            sentiment = labels[int(row.prediction)]
            push_live(row.reviewText, sentiment, datetime.utcnow())

    query = (
        preds.writeStream
             .foreachBatch(foreach_batch)
             .outputMode("append")
             .start()
    )

    query.awaitTermination()

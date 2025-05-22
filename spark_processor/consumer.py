# spark_processor/consumer.py

from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import from_json, col, rand
from pyspark.sql.types import StructType, StringType
from pymongo import MongoClient

if __name__ == "__main__":
    # 1️⃣ Initialize Spark
    spark = SparkSession.builder \
        .appName("KafkaToMongo") \
        .getOrCreate()

    # 2️⃣ Define schema for incoming JSON reviews
    schema = StructType().add("reviewText", StringType())

    # 3️⃣ Load your pre-trained ML pipeline
    model = PipelineModel.load("/app/rf_pipeline_amazon_json")

    # 4️⃣ Extract StringIndexer stage labels (e.g. ['negative','neutral','positive'])
    labels = None
    for stage in model.stages:
        if hasattr(stage, "labels"):
            labels = list(stage.labels)
            break
    if labels is None:
        labels = ["negative", "neutral", "positive"]

    # 5️⃣ Connect to MongoDB
    mongo_client = MongoClient("mongo", 27017)
    db = mongo_client["amazon"]
    collection = db["reviews"]

    # 6️⃣ Read streaming data from Kafka
    kafka_df = (
        spark.readStream
             .format("kafka")
             .option("kafka.bootstrap.servers", "kafka:9092")
             .option("subscribe", "amazon-reviews")
             .option("startingOffsets", "earliest")
             .load()
    )

    # 7️⃣ Parse JSON and add isTest flag (10% of data)
    reviews_df = (
        kafka_df
          .selectExpr("CAST(value AS STRING) AS json_str")
          .select(from_json(col("json_str"), schema).alias("data"))
          .select("data.reviewText")
          .withColumn("isTest", (rand() < 0.1))
    )

    # 8️⃣ Apply the ML pipeline to get predictions
    preds = model.transform(reviews_df) \
                 .select("reviewText", "prediction", "isTest")

    # 9️⃣ Write each micro-batch to MongoDB
    def write_to_mongo(batch_df, batch_id):
        docs = []
        for row in batch_df.collect():
            idx = int(row.prediction)
            sentiment = labels[idx] if idx < len(labels) else "unknown"
            docs.append({
                "review": row.reviewText,
                "sentiment": sentiment,
                "timestamp": datetime.utcnow(),
                "isTest": bool(row.isTest)
            })
        if docs:
            collection.insert_many(docs)

    # 🔟 Start the streaming query
    query = (
        preds.writeStream
             .foreachBatch(write_to_mongo)
             .outputMode("append")
             .option("checkpointLocation", "/app/checkpoint")
             .start()
    )

    query.awaitTermination()

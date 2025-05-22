# spark_processor/consumer.py

from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType, StringType
from pymongo import MongoClient

if __name__ == "__main__":
    # 1. Initialize Spark session
    spark = SparkSession.builder \
        .appName("KafkaToMongo") \
        .getOrCreate()

    # 2. Define the JSON schema for incoming reviews
    schema = StructType().add("reviewText", StringType())

    # 3. Load your saved MLlib pipeline
    #    (folder name kept exactly as rf_pipeline_amazon_json)
    model = PipelineModel.load("/app/rf_pipeline_amazon_json")

    # 4. Connect to MongoDB at service name "mongo"
    mongo_client = MongoClient("mongo", 27017)
    db = mongo_client["amazon"]
    collection = db["reviews"]

    # 5. Read streaming data from Kafka topic "amazon-reviews"
    kafka_df = (
        spark.readStream
             .format("kafka")
             .option("kafka.bootstrap.servers", "kafka:9092")
             .option("subscribe", "amazon-reviews")
             .option("startingOffsets", "earliest")
             .load()
    )

    # 6. Parse the JSON payload into a DataFrame of review texts
    reviews_df = (
        kafka_df
          .selectExpr("CAST(value AS STRING) AS json_str")
          .select(from_json(col("json_str"), schema).alias("data"))
          .select("data.reviewText")
    )

    # 7. Apply the ML pipeline to produce predictions
    preds = model.transform(reviews_df).select("reviewText", "prediction")

    # 8. Define a function to write each micro-batch into MongoDB
    def write_to_mongo(batch_df, batch_id):
        batch = batch_df.collect()
        if not batch:
            return
        docs = [
            {
                "review": row.reviewText,
                "sentiment": "positive" if row.prediction == 1.0 else "negative"
            }
            for row in batch
        ]
        collection.insert_many(docs)

    # 9. Set up and start the streaming query
    query = (
        preds.writeStream
             .foreachBatch(write_to_mongo)
             .outputMode("append")
             .start()
    )

    # 10. Await termination (run until manually stopped)
    query.awaitTermination()

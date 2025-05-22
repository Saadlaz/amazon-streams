
import os

# Set JAVA_HOME for PySpark to launch the JVM correctly
os.environ["JAVA_HOME"] = r"C:\Program Files\Eclipse Adoptium\jdk-11.0.27.6-hotspot"




from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StringType, DoubleType, ArrayType

def main():
    # 1) SparkSession with Kafka support
    spark = SparkSession.builder \
        .appName("KafkaReviewClassifier") \
        .config("spark.sql.shuffle.partitions", "2") \
        .config("spark.streaming.stopGracefullyOnShutdown","true") \
        .getOrCreate()

    # 2) Load your saved pipeline (all stages: tokenizer, cv, idf, classifier, etc)
    pipeline = PipelineModel.load("models/amazon_sentiment_model_lr")

    # 3) Define the JSON schema of your Kafka messages
    schema = StructType() \
        .add("reviewerID", StringType()) \
        .add("asin",       StringType()) \
        .add("reviewerName", StringType()) \
        .add("helpful",    ArrayType(DoubleType())) \
        .add("reviewText", StringType()) \
        .add("overall",    DoubleType()) \
        .add("summary",    StringType()) \
        .add("unixReviewTime", DoubleType()) \
        .add("reviewTime", StringType())

    # 4) Read from Kafka
    raw = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "amazon-reviews") \
        .option("startingOffsets", "latest") \
        .load()

    # 5) Extract the JSON string and parse it
    json_df = raw.selectExpr("CAST(value AS STRING) as json_str") \
                 .select(from_json(col("json_str"), schema).alias("data")) \
                 .select("data.*")

    # 6) Apply your pipeline to classify
    predictions = pipeline.transform(json_df)

    # 7) Select only the fields you care about
    output = predictions.select(
        col("reviewText"),
        col("prediction").cast("integer"),
        col("probability")
    )

    # 8) Write to console for testing
    query = output.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()

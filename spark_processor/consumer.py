# spark_processor/consumer.py

from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel, Transformer
from pyspark.sql.functions import from_json, col, rand, lower, udf
from pyspark.sql.types import StructType, StringType, ArrayType
from pyspark.ml.param.shared import HasInputCol, HasOutputCol
from pyspark.ml.util import DefaultParamsReadable, DefaultParamsWritable
from pymongo import MongoClient
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import requests

# ======================== NLTK Setup ========================
nltk.download('stopwords')
nltk.download('wordnet')

stop_words = set(stopwords.words('english'))
stop_words.remove("not")  # Keep 'not' for sentiment

lemmatizer = WordNetLemmatizer()

# ======================== UDFs ========================
def stopwords_remove(tokens):
    return [word for word in tokens if word not in stop_words]
stopwords_remove_udf = udf(stopwords_remove, ArrayType(StringType()))

def lemmatization(tokens):
    return [lemmatizer.lemmatize(word, pos='v') for word in tokens]
lemmatization_udf = udf(lemmatization, ArrayType(StringType()))

def remove_short_words(tokens):
    return [word for word in tokens if len(word) > 2]
remove_short_words_udf = udf(remove_short_words, ArrayType(StringType()))

# ======================== Custom Transformers ========================
class LowerTransformer(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)
    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), lower(col(self.getInputCol())))

class StopwordsRemover(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)
    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), stopwords_remove_udf(col(self.getInputCol())))

class Lemmatizer(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)
    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), lemmatization_udf(col(self.getInputCol())))

class ShortWordRemover(Transformer, HasInputCol, HasOutputCol, DefaultParamsWritable, DefaultParamsReadable):
    def __init__(self, inputCol=None, outputCol=None):
        super().__init__()
        self._set(inputCol=inputCol, outputCol=outputCol)
    def _transform(self, dataset):
        return dataset.withColumn(self.getOutputCol(), remove_short_words_udf(col(self.getInputCol())))

# ======================== Live Push Setup ========================
def push_live(payload):
    try:
        requests.post(
            "http://dashboard:8000/reviews/api/push/",
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"[write_live] Failed to push live review: {e}")

def write_live(batch_df, batch_id):
    for row in batch_df.collect():
        sentiment = labels[int(row.prediction)]
        payload = {
            "review":    row.reviewText,
            "sentiment": sentiment,
            "timestamp": datetime.utcnow().isoformat()
        }
        push_live(payload)

# ======================== Main Pipeline ========================
if __name__ == "__main__":
    spark = SparkSession.builder \
        .appName("KafkaToMongo") \
        .getOrCreate()

    schema = StructType().add("reviewText", StringType())

    # Load trained ML model pipeline
    model = PipelineModel.load("/app/rf_pipeline_amazon_json")

    # Extract label index → sentiment name
    labels = None
    for stage in model.stages:
        if hasattr(stage, "labels"):
            labels = list(stage.labels)
            break
    if labels is None:
        labels = ["negative", "neutral", "positive"]

    # Connect to MongoDB
    mongo_client = MongoClient("mongo", 27017)
    db = mongo_client["amazon"]
    collection = db["reviews"]

    # Read streaming data from Kafka
    kafka_df = (
        spark.readStream
             .format("kafka")
             .option("kafka.bootstrap.servers", "kafka:9092")
             .option("subscribe", "amazon-reviews")
             .option("startingOffsets", "earliest")
             .load()
    )

    # Parse JSON and add isTest column
    reviews_df = (
        kafka_df
            .selectExpr("CAST(value AS STRING) AS json_str")
            .select(from_json(col("json_str"), schema).alias("data"))
            .select("data.reviewText")
            .withColumn("isTest", rand() < 0.1)
    )

    # Apply the pipeline to get predictions
    preds = model.transform(reviews_df) \
                 .select("reviewText", "prediction", "isTest")

    # Write each batch to MongoDB
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

    # Optional: Use this if you want both Mongo and live push
    def dual_writer(batch_df, batch_id):
        write_to_mongo(batch_df, batch_id)
        write_live(batch_df, batch_id)

    # Start the streaming query
    query = (
        preds.writeStream
             .foreachBatch(dual_writer)
             .outputMode("append")
             .option("checkpointLocation", "/app/checkpoint")
             .start()
    )

    query.awaitTermination()
